import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from workcell.models import CellError


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Durable accounting; one controller process may own a database at a time."""

    def __init__(self, path: str, capacity: int, fingerprint: str):
        self.lock = threading.RLock()
        self._lease = None
        if path != ":memory:":
            target = Path(path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            self._lease = open(str(target) + ".lock", "a+b")
            self._lease.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    if target.with_suffix(target.suffix + ".lock").stat().st_size == 0:
                        self._lease.write(b"0")
                        self._lease.flush()
                    self._lease.seek(0)
                    msvcrt.locking(self._lease.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                self._lease.close()
                raise CellError("Another controller owns this database") from exc
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS slots(id INTEGER PRIMARY KEY, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cycles(
                id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT NOT NULL, ended TEXT,
                request_id INTEGER NOT NULL, part TEXT NOT NULL, slot INTEGER,
                status TEXT NOT NULL, error TEXT, config_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
                kind TEXT NOT NULL, detail TEXT NOT NULL);
        """)
        existing = self.get_meta("config_hash")
        if existing and existing != fingerprint:
            self.close()
            raise CellError(
                "Database belongs to a different configuration. Archive it and use a new database after reconciling the cell."
            )
        self.fingerprint = fingerprint
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO slots VALUES (?, 'EMPTY')", [(i,) for i in range(capacity)]
            )
            self.db.execute("INSERT OR REPLACE INTO meta VALUES ('config_hash', ?)", (fingerprint,))
            interrupted = self.db.execute(
                "SELECT COUNT(*) FROM cycles WHERE status='RUNNING'"
            ).fetchone()[0]
            if interrupted:
                self.db.execute(
                    "UPDATE cycles SET status='INTERRUPTED', ended=?, error=? WHERE status='RUNNING'",
                    (utc_now(), "Controller stopped during cycle"),
                )
                self.db.execute("UPDATE slots SET status='UNKNOWN' WHERE status='RESERVED'")
                self.db.execute(
                    "INSERT OR REPLACE INTO meta VALUES ('fault', ?)",
                    (
                        "Interrupted cycle: inspect gripper, destination, and pallet before recovery",
                    ),
                )

    def get_meta(self, key: str) -> str | None:
        with self.lock:
            row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else None

    def set_meta(self, key: str, value: str):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))

    def event(self, kind: str, detail):
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO events(at,kind,detail) VALUES (?,?,?)",
                (utc_now(), kind, json.dumps(detail)),
            )

    def slots(self) -> list[dict]:
        with self.lock:
            return [dict(row) for row in self.db.execute("SELECT * FROM slots ORDER BY id")]

    def begin(self, part: str, request_id: int, pallet: bool) -> tuple[int, int | None]:
        with self.lock, self.db:
            if self.db.execute("SELECT 1 FROM slots WHERE status='UNKNOWN'").fetchone():
                raise CellError("Resolve unknown pallet slots before starting")
            slot = None
            if pallet:
                row = self.db.execute(
                    "SELECT id FROM slots WHERE status='EMPTY' ORDER BY id LIMIT 1"
                ).fetchone()
                if row is None:
                    raise CellError("Pallet is full")
                slot = row[0]
                self.db.execute("UPDATE slots SET status='RESERVED' WHERE id=?", (slot,))
            result = self.db.execute(
                "INSERT INTO cycles(started,request_id,part,slot,status,config_hash) VALUES (?,?,?,?,'RUNNING',?)",
                (utc_now(), request_id, part, slot, self.fingerprint),
            )
            return result.lastrowid, slot

    def placed(self, slot: int | None):
        if slot is not None:
            with self.lock, self.db:
                result = self.db.execute(
                    "UPDATE slots SET status='OCCUPIED' WHERE id=? AND status='RESERVED'", (slot,)
                )
                if result.rowcount != 1:
                    raise CellError("Pallet reservation was lost")

    def finish(self, cycle: int, error: str | None = None):
        with self.lock, self.db:
            if error:
                self.db.execute(
                    "UPDATE slots SET status='UNKNOWN' WHERE id=(SELECT slot FROM cycles WHERE id=?) AND status='RESERVED'",
                    (cycle,),
                )
            self.db.execute(
                "UPDATE cycles SET status=?,error=?,ended=? WHERE id=?",
                ("FAULT" if error else "COMPLETE", error, utc_now(), cycle),
            )

    def reconcile(self, slot: int, occupied: bool, note: str):
        with self.lock, self.db:
            result = self.db.execute(
                "UPDATE slots SET status=? WHERE id=? AND status='UNKNOWN'",
                ("OCCUPIED" if occupied else "EMPTY", slot),
            )
            if result.rowcount != 1:
                raise CellError("Only UNKNOWN slots can be reconciled")
        self.event("reconcile", {"slot": slot, "occupied": occupied, "note": note})

    def replace_pallet(self, note: str):
        with self.lock, self.db:
            if self.db.execute(
                "SELECT 1 FROM slots WHERE status IN ('UNKNOWN','RESERVED')"
            ).fetchone():
                raise CellError("Reconcile uncertain slots before replacing the pallet")
            self.db.execute("UPDATE slots SET status='EMPTY'")
        self.event("pallet_replaced", {"note": note})

    def history(self) -> dict:
        with self.lock:
            return {
                "cycles": [
                    dict(r)
                    for r in self.db.execute("SELECT * FROM cycles ORDER BY id DESC LIMIT 30")
                ],
                "events": [
                    dict(r)
                    for r in self.db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")
                ],
            }

    def close(self):
        self.db.close()
        if self._lease:
            self._lease.close()
            self._lease = None
