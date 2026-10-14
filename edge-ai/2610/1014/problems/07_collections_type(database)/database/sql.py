from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "mountain.db"


def get_connection() -> sqlite3.Connection:
    """DB 연결 객체를 생성하고 컬럼명 접근이 가능하도록 row_factory 설정"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """테이블 생성 (프로그램 시작 시 1회 실행)"""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mountain (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                location TEXT,
                height TEXT
            )
            """
        )
        conn.commit()


def add_mountain_to_db(name: str, location: str, height: str) -> bool:
    """산행지 등록 (중복 산 이름이면 False 반환)"""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO mountain (name, location, height) VALUES (?, ?, ?)",
                (name, location, height),
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        # UNIQUE 제약조건 위반(중복된 산 이름)
        return False


def get_mountain_by_name(name: str) -> dict | None:
    """이름으로 특정 산행지 1건 검색"""
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT name, location, height FROM mountain WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_mountains() -> list[dict]:
    """전체 산행지 목록 조회"""
    with get_connection() as conn:
        cursor = conn.execute("SELECT name, location, height FROM mountain")
        return [dict(row) for row in cursor.fetchall()]


def delete_mountain_from_db(name: str) -> bool:
    """특정 산행지 1건 삭제 (삭제 대상이 없으면 False 반환)"""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM mountain WHERE name = ?", (name,))
        conn.commit()
        # rowcount: 실제로 영향을 받은(삭제된) 행의 개수
        return cursor.rowcount > 0