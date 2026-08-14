"""
database.py - SQLite 데이터베이스 관리
"""

import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# ----- 설정 -----
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chat.db")
# 메시지 보관 기간 (일 단위) - 이 값만 변경하면 됨
MESSAGE_RETENTION_DAYS = 7
# ----------------


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
    cutoff = datetime.now(timezone.utc) - timedelta(days=MESSAGE_RETENTION_DAYS)
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
    """보관 기간 내 최근 메시지를 시간 오름차순으로 반환한다. (ip 제외해서 클라이언트에 노출 안 함)"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=MESSAGE_RETENTION_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, nickname, content, created_at
            FROM messages
            WHERE created_at >= ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (cutoff_str, limit),
        ).fetchall()
    return [dict(row) for row in rows]
