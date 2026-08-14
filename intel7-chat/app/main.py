"""
main.py - FastAPI 서버 (WebSocket 채팅 + SQLite 저장)
"""

import asyncio
import ipaddress
import json
import logging
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, Set
from urllib.parse import urlsplit

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import (
    delete_expired_messages,
    get_ip_suffix,
    get_recent_messages,
    init_db,
    save_message,
)

# --------- 설정 ---------
SERVICE_NAME = "인텔7기 대나무숲"
MAX_NICKNAME_LEN = 30
MAX_CONTENT_LEN = 500
CLEANUP_INTERVAL_SECONDS = 3600  # 1시간마다 만료 메시지 삭제
MAX_RAW_MESSAGE_LEN = 2048
MAX_CONNECTIONS_TOTAL = 50
MAX_CONNECTIONS_PER_IP = 3
RATE_LIMIT_MESSAGES = 30
RATE_LIMIT_WINDOW_SECONDS = 10
EXPLICIT_ALLOWED_HOSTS = {
    host.strip().casefold()
    for host in os.getenv("CLASSROOM_ALLOWED_HOSTS", "").split(",")
    if host.strip()
}
# ------------------------

logger = logging.getLogger("classroom_chat")


@dataclass(frozen=True)
class ClientInfo:
    nickname: str
    ip: str


# 연결된 WebSocket 클라이언트: {WebSocket: ClientInfo}
connected_clients: Dict[WebSocket, ClientInfo] = {}
# 닉네임 → WebSocket 레지스트리 (중복 방지)
nickname_registry: Dict[str, WebSocket] = {}
# IP별 최근 메시지 수 (간단한 프로세스 내 rate limit)
message_timestamps: Dict[str, Deque[float]] = defaultdict(deque)


def get_client_ip(ws_or_request) -> str:
    """WebSocket 또는 Request에서 클라이언트 IP를 추출한다."""
    try:
        return ws_or_request.client.host or ""
    except Exception:
        return ""


def suggest_nickname(ip: str) -> str:
    """IP 마지막 옥텟으로 기본 닉네임을 생성한다."""
    if not ip:
        return "사용자"
    last = ip.split(".")[-1] if "." in ip else ip.split(":")[-1]
    return f"사용자{last}"


def host_is_allowed(host_header: str) -> bool:
    """공개 DNS rebinding을 막으면서 일반 LAN 이름과 사설 IP는 허용한다."""
    try:
        hostname = urlsplit(f"//{host_header}").hostname
    except ValueError:
        return False
    if not hostname:
        return False
    hostname = hostname.casefold().rstrip(".")
    if hostname in EXPLICIT_ALLOWED_HOSTS or hostname == "localhost":
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return "." not in hostname or hostname.endswith(".local")
    return address.is_private or address.is_loopback or address.is_link_local


def websocket_origin_is_allowed(ws: WebSocket) -> bool:
    """브라우저가 허용된 LAN host의 동일 origin 페이지에서 연결했는지 확인한다."""
    origin = ws.headers.get("origin", "")
    host = ws.headers.get("host", "")
    if not origin or not host or not host_is_allowed(host):
        return False
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and parsed.netloc.casefold() == host.casefold()


def connection_limit_reason(client_ip: str) -> str:
    """연결 가능하면 빈 문자열, 제한을 넘으면 사용자용 사유를 반환한다."""
    if len(connected_clients) >= MAX_CONNECTIONS_TOTAL:
        return "서버의 최대 접속 인원에 도달했습니다. 잠시 후 다시 시도하세요."
    per_ip = sum(info.ip == client_ip for info in connected_clients.values())
    if per_ip >= MAX_CONNECTIONS_PER_IP:
        return "같은 기기에서 너무 많은 연결이 열려 있습니다. 다른 탭을 닫고 다시 시도하세요."
    return ""


def message_rate_allowed(client_ip: str, now: float | None = None) -> bool:
    """IP별 sliding-window 메시지 제한을 적용한다."""
    current = time.monotonic() if now is None else now
    timestamps = message_timestamps[client_ip]
    cutoff = current - RATE_LIMIT_WINDOW_SECONDS
    while timestamps and timestamps[0] <= cutoff:
        timestamps.popleft()
    if len(timestamps) >= RATE_LIMIT_MESSAGES:
        return False
    timestamps.append(current)
    return True


async def broadcast(payload: dict) -> None:
    """연결된 모든 클라이언트에게 JSON 메시지를 전송한다."""
    message = json.dumps(payload, ensure_ascii=False)
    dead: Set[WebSocket] = set()
    for ws in list(connected_clients.keys()):
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _remove_client(ws)


def _remove_client(ws: WebSocket) -> None:
    """클라이언트를 레지스트리에서 제거한다."""
    info = connected_clients.pop(ws, None)
    if info and nickname_registry.get(info.nickname) is ws:
        del nickname_registry[info.nickname]


async def broadcast_presence() -> None:
    """현재 접속자 수를 모든 클라이언트에게 전송한다."""
    await broadcast({"type": "presence", "count": len(connected_clients)})


async def broadcast_users() -> None:
    """현재 접속자 닉네임과 화면 표시용 IP 끝자리를 전송한다."""
    users = [
        {"nickname": info.nickname, "ip_suffix": get_ip_suffix(info.ip)}
        for info in connected_clients.values()
    ]
    await broadcast({"type": "users", "list": users})


async def _cleanup_loop() -> None:
    """주기적으로 만료 메시지를 삭제하는 백그라운드 태스크."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        deleted = delete_expired_messages()
        if deleted:
            print(f"[cleanup] 만료 메시지 {deleted}건 삭제")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("[startup] DB 초기화 완료")
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=SERVICE_NAME,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if not host_is_allowed(request.headers.get("host", "")):
        logger.warning("Rejected HTTP host=%r ip=%s", request.headers.get("host"), get_client_ip(request))
        return PlainTextResponse("Invalid host", status_code=400)
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'self'; img-src 'self'; style-src 'self'; "
        "script-src 'self'; connect-src 'self' ws: wss:"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 채팅 페이지를 반환한다."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"service_name": SERVICE_NAME},
    )


@app.get("/api/client-info")
async def client_info(request: Request):
    """클라이언트 IP 기반 추천 닉네임을 반환한다."""
    ip = get_client_ip(request)
    return {
        "suggested_nickname": suggest_nickname(ip),
        "ip_last_octet": ip.split(".")[-1] if "." in ip else "",
    }


@app.get("/api/messages")
async def api_messages():
    """최근 메시지 목록을 반환한다. (ip 필드 제외)"""
    return get_recent_messages()


@app.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    nickname: str = Query(""),
):
    """WebSocket 채팅 엔드포인트.
    닉네임을 쿼리 파라미터로 받아 중복 여부를 확인하고 연결한다.
    """
    nickname = nickname.strip()
    client_ip = get_client_ip(ws)

    if not websocket_origin_is_allowed(ws):
        logger.warning("Rejected WebSocket origin ip=%s origin=%r", client_ip, ws.headers.get("origin"))
        await ws.close(code=1008, reason="허용되지 않은 WebSocket origin입니다.")
        return

    await ws.accept()

    limit_reason = connection_limit_reason(client_ip)
    if limit_reason:
        logger.warning("Rejected connection limit ip=%s", client_ip)
        await ws.send_text(json.dumps({"type": "error", "message": limit_reason}, ensure_ascii=False))
        await ws.close(code=1013)
        return

    # 닉네임 유효성 검사
    if not nickname or len(nickname) > MAX_NICKNAME_LEN:
        await ws.send_text(json.dumps({
            "type": "error_nickname",
            "message": f"닉네임이 비어 있거나 {MAX_NICKNAME_LEN}자를 초과합니다.",
        }, ensure_ascii=False))
        await ws.close(code=1008)
        return

    # 중복 닉네임 차단
    if nickname in nickname_registry:
        await ws.send_text(json.dumps({
            "type": "error_nickname",
            "message": f"'{nickname}' 닉네임은 이미 사용 중입니다. 다른 닉네임을 사용하세요.",
        }, ensure_ascii=False))
        await ws.close(code=1008)
        return

    # 등록
    connected_clients[ws] = ClientInfo(nickname=nickname, ip=client_ip)
    nickname_registry[nickname] = ws
    logger.info("Connected nickname=%r ip=%s", nickname, client_ip)
    await broadcast_presence()
    await broadcast_users()

    # 입장 시 최근 메시지 전송
    recent = get_recent_messages()
    for msg in recent:
        await ws.send_text(json.dumps({
            "type": "chat",
            "nickname": msg["nickname"],
            "ip_suffix": msg["ip_suffix"],
            "content": msg["content"],
            "created_at": msg["created_at"],
        }, ensure_ascii=False))

    try:
        while True:
            raw = await ws.receive_text()
            if len(raw) > MAX_RAW_MESSAGE_LEN:
                logger.warning("Oversized WebSocket message nickname=%r ip=%s length=%s", nickname, client_ip, len(raw))
                await ws.close(code=1009, reason="메시지 프레임이 너무 큽니다.")
                break
            if not message_rate_allowed(client_ip):
                logger.warning("Rate limit exceeded nickname=%r ip=%s", nickname, client_ip)
                await ws.send_text(json.dumps({
                    "type": "error",
                    "message": "메시지를 너무 빠르게 보내고 있습니다. 잠시 후 다시 접속하세요.",
                }, ensure_ascii=False))
                await ws.close(code=1008)
                break
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict):
                continue

            msg_type = data.get("type")

            # ── 공개 채팅 ──
            if msg_type == "chat":
                content = str(data.get("content", "")).strip()
                if not content:
                    continue
                if len(content) > MAX_CONTENT_LEN:
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "message": f"메시지는 {MAX_CONTENT_LEN}자 이하여야 합니다.",
                    }, ensure_ascii=False))
                    continue
                saved = save_message(nickname, content, ip=client_ip)
                await broadcast({
                    "type": "chat",
                    "nickname": saved["nickname"],
                    "ip_suffix": get_ip_suffix(saved["ip"]),
                    "content": saved["content"],
                    "created_at": saved["created_at"],
                })

            # ── DM (1:1 메시지) ──
            elif msg_type == "dm":
                to_nick = str(data.get("to", "")).strip()
                content  = str(data.get("content", "")).strip()
                if not to_nick or not content:
                    continue
                if len(content) > MAX_CONTENT_LEN:
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "message": f"메시지는 {MAX_CONTENT_LEN}자 이하여야 합니다.",
                    }, ensure_ascii=False))
                    continue
                target_ws = nickname_registry.get(to_nick)
                if not target_ws:
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "message": f"'{to_nick}'님이 오프라인 상태입니다.",
                    }, ensure_ascii=False))
                    continue
                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                target_info = connected_clients.get(target_ws)
                dm_payload = json.dumps({
                    "type": "dm",
                    "from_nick": nickname,
                    "to_nick": to_nick,
                    "from_ip_suffix": get_ip_suffix(client_ip),
                    "to_ip_suffix": get_ip_suffix(target_info.ip if target_info else ""),
                    "content": content,
                    "created_at": now,
                }, ensure_ascii=False)
                # 수신자에게 전달
                try:
                    await target_ws.send_text(dm_payload)
                except Exception:
                    pass
                # 발신자에게 에코 (전송 확인)
                await ws.send_text(dm_payload)

    except WebSocketDisconnect:
        pass
    finally:
        _remove_client(ws)
        logger.info("Disconnected nickname=%r ip=%s", nickname, client_ip)
        await broadcast_presence()
        await broadcast_users()
