"""
main.py - FastAPI 서버 (WebSocket 채팅 + SQLite 저장)
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Set, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db, save_message, get_recent_messages, delete_expired_messages

# --------- 설정 ---------
SERVICE_NAME = "인텔7기 대나무숲"
MAX_NICKNAME_LEN = 30
MAX_CONTENT_LEN = 500
CLEANUP_INTERVAL_SECONDS = 36000  # 1시간마다 만료 메시지 삭제
# ------------------------

# 연결된 WebSocket 클라이언트: {WebSocket: nickname}
connected_clients: Dict[WebSocket, str] = {}
# 닉네임 → WebSocket 레지스트리 (중복 방지)
nickname_registry: Dict[str, WebSocket] = {}


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
    nick = connected_clients.pop(ws, None)
    if nick and nickname_registry.get(nick) is ws:
        del nickname_registry[nick]


async def broadcast_presence() -> None:
    """현재 접속자 수를 모든 클라이언트에게 전송한다."""
    await broadcast({"type": "presence", "count": len(connected_clients)})


async def broadcast_users() -> None:
    """현재 접속자 닉네임 목록을 모든 클라이언트에게 전송한다."""
    await broadcast({"type": "users", "list": list(nickname_registry.keys())})


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


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)

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

    await ws.accept()

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
    connected_clients[ws] = nickname
    nickname_registry[nickname] = ws
    print(f"[connect] {nickname} ({client_ip})")
    await broadcast_presence()
    await broadcast_users()

    # 입장 시 최근 메시지 전송
    recent = get_recent_messages()
    for msg in recent:
        await ws.send_text(json.dumps({
            "type": "chat",
            "nickname": msg["nickname"],
            "content": msg["content"],
            "created_at": msg["created_at"],
        }, ensure_ascii=False))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
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
                dm_payload = json.dumps({
                    "type": "dm",
                    "from_nick": nickname,
                    "to_nick": to_nick,
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
        print(f"[disconnect] {nickname} ({client_ip})")
        await broadcast_presence()
        await broadcast_users()
