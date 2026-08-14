"""
database.py - SQLite 데이터베이스 관리
"""

import ipaddress
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# ----- 설정 -----
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chat.db")
# 공개 메시지와 기록된 IP의 보관 기간 (시간 단위)
MESSAGE_RETENTION_HOURS = 10
# ----------------


def get_ip_suffix(ip: str) -> str:
    """화면 표시용으로 IPv4 마지막 두 옥텟(IPv6는 마지막 두 그룹)만 반환한다."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ""
    if isinstance(address, ipaddress.IPv4Address):
        return ".".join(str(address).split(".")[-2:])
    return ":".join(address.exploded.split(":")[-2:])


def get_connection() -> sqlite3.Connection:
    """DB 연결을 반환한다."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """테이블을 초기화하고, ip 컬럼 마이그레이션, 만료 메시지 삭제."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname   TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                ip         TEXT    NOT NULL DEFAULT ''
            )
        """)
        conn.commit()

        # 기존 DB에 ip 컬럼이 없으면 추가 (마이그레이션)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()]
        if "ip" not in cols:
            conn.execute("ALTER TABLE messages ADD COLUMN ip TEXT NOT NULL DEFAULT ''")
            conn.commit()
            print("[db] ip 컬럼 마이그레이션 완료")

    delete_expired_messages()


def delete_expired_messages() -> int:
    """보관 기간이 지난 메시지를 삭제하고 삭제된 건수를 반환한다."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MESSAGE_RETENTION_HOURS)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM messages WHERE created_at < ?", (cutoff_str,)
        )
        conn.commit()
        return cursor.rowcount


def save_message(nickname: str, content: str, ip: str = "") -> Dict[str, Any]:
    """메시지를 저장하고 저장된 레코드를 반환한다. ip는 관리 목적으로 기록."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (nickname, content, created_at, ip) VALUES (?, ?, ?, ?)",
            (nickname, content, now, ip),
        )
        conn.commit()
        row_id = cursor.lastrowid
    return {"id": row_id, "nickname": nickname, "content": content, "created_at": now, "ip": ip}


def get_recent_messages(limit: int = 100) -> List[Dict[str, Any]]:
    """보관 기간 내 최근 메시지를 반환한다. 전체 IP는 제외하고 화면용 suffix만 포함한다."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MESSAGE_RETENTION_HOURS)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, nickname, content, created_at, ip
            FROM messages
            WHERE created_at >= ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (cutoff_str, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "nickname": row["nickname"],
            "content": row["content"],
            "created_at": row["created_at"],
            "ip_suffix": get_ip_suffix(row["ip"]),
        }
        for row in rows
    ]
