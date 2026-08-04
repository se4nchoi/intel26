from __future__ import annotations

import hmac
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from database import Database, hash_password


class LibraryError(Exception):
    """A friendly business-rule error that can be shown in the interface."""


@dataclass(frozen=True)
class User:
    id: int
    card_id: str
    name: str
    is_admin: bool


class LibraryService:
    MAX_ACTIVE_LOANS = 3

    def __init__(self, database: Database) -> None:
        self.database = database

    def authenticate(self, card_id: str, password: str) -> User | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT id, card_id, name, password_hash, password_salt, is_admin
                   FROM users WHERE card_id = ?""",
                (card_id.strip(),),
            ).fetchone()
        if row is None:
            return None
        candidate = hash_password(password, row["password_salt"])
        if not hmac.compare_digest(candidate, row["password_hash"]):
            return None
        return User(row["id"], row["card_id"], row["name"], bool(row["is_admin"]))

    def search_books(self, query: str = "") -> list[sqlite3.Row]:
        pattern = f"%{query.strip()}%"
        with self.database.connect() as connection:
            return connection.execute(
                """
                SELECT b.id, b.title, b.author, b.isbn,
                       NOT EXISTS (
                           SELECT 1 FROM loans l
                           WHERE l.book_id = b.id AND l.returned_at IS NULL
                       ) AS available
                FROM books b
                WHERE b.is_active = 1
                  AND (b.title LIKE ? COLLATE NOCASE
                   OR b.author LIKE ? COLLATE NOCASE
                   OR b.isbn LIKE ? COLLATE NOCASE)
                ORDER BY b.title
                """,
                (pattern, pattern, pattern),
            ).fetchall()

    @staticmethod
    def _validated_book_fields(title: str, author: str, isbn: str) -> tuple[str, str, str]:
        fields = (title.strip(), author.strip(), isbn.strip())
        if not all(fields):
            raise LibraryError("Title, author, and ISBN are required.")
        return fields

    @staticmethod
    def _require_admin(connection: sqlite3.Connection, user_id: int) -> None:
        row = connection.execute(
            "SELECT is_admin FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None or not row["is_admin"]:
            raise LibraryError("Administrator access is required.")

    def add_book(self, user_id: int, title: str, author: str, isbn: str) -> int:
        title, author, isbn = self._validated_book_fields(title, author, isbn)
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_admin(connection, user_id)
            try:
                cursor = connection.execute(
                    "INSERT INTO books (title, author, isbn) VALUES (?, ?, ?)",
                    (title, author, isbn),
                )
            except sqlite3.IntegrityError as error:
                raise LibraryError("A book with that ISBN already exists.") from error
            return cursor.lastrowid

    def update_book(
        self, user_id: int, book_id: int, title: str, author: str, isbn: str
    ) -> None:
        title, author, isbn = self._validated_book_fields(title, author, isbn)
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_admin(connection, user_id)
            try:
                cursor = connection.execute(
                    """UPDATE books SET title = ?, author = ?, isbn = ?
                       WHERE id = ? AND is_active = 1""",
                    (title, author, isbn, book_id),
                )
            except sqlite3.IntegrityError as error:
                raise LibraryError("A book with that ISBN already exists.") from error
            if cursor.rowcount != 1:
                raise LibraryError("Please select a valid catalogue entry.")

    def archive_books(self, user_id: int, book_ids: Iterable[int]) -> int:
        selected_ids = sorted(set(book_ids))
        if not selected_ids:
            raise LibraryError("Select at least one catalogue entry.")
        placeholders = ", ".join("?" for _ in selected_ids)
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._require_admin(connection, user_id)
            found = connection.execute(
                f"SELECT COUNT(*) FROM books WHERE is_active = 1 AND id IN ({placeholders})",
                selected_ids,
            ).fetchone()[0]
            if found != len(selected_ids):
                raise LibraryError("One or more selected catalogue entries no longer exist.")
            cursor = connection.execute(
                f"UPDATE books SET is_active = 0 WHERE id IN ({placeholders})",
                selected_ids,
            )
            return cursor.rowcount

    def active_loans(self, user_id: int) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return connection.execute(
                """SELECT l.id, b.title, l.borrowed_at, l.due_at
                   FROM loans l JOIN books b ON b.id = l.book_id
                   WHERE l.user_id = ? AND l.returned_at IS NULL
                   ORDER BY l.due_at, b.title""",
                (user_id,),
            ).fetchall()

    def borrow_book(self, user_id: int, book_id: int, today: date | None = None) -> None:
        borrowed_at = today or date.today()
        due_at = borrowed_at + timedelta(days=14)
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
                raise LibraryError("The current user no longer exists.")
            if connection.execute(
                "SELECT 1 FROM books WHERE id = ? AND is_active = 1", (book_id,)
            ).fetchone() is None:
                raise LibraryError("Please select a valid book.")
            active_count = connection.execute(
                "SELECT COUNT(*) FROM loans WHERE user_id = ? AND returned_at IS NULL",
                (user_id,),
            ).fetchone()[0]
            if active_count >= self.MAX_ACTIVE_LOANS:
                raise LibraryError("You may borrow up to three books at a time.")
            unavailable = connection.execute(
                "SELECT 1 FROM loans WHERE book_id = ? AND returned_at IS NULL",
                (book_id,),
            ).fetchone()
            if unavailable:
                raise LibraryError("That book is currently unavailable.")
            try:
                connection.execute(
                    """INSERT INTO loans
                       (user_id, book_id, borrowed_at, due_at, returned_at)
                       VALUES (?, ?, ?, ?, NULL)""",
                    (user_id, book_id, borrowed_at.isoformat(), due_at.isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise LibraryError("That book is currently unavailable.") from error

    def return_loan(self, user_id: int, loan_id: int, today: date | None = None) -> None:
        returned_at = (today or date.today()).isoformat()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE loans SET returned_at = ?
                   WHERE id = ? AND user_id = ? AND returned_at IS NULL""",
                (returned_at, loan_id, user_id),
            )
            if cursor.rowcount != 1:
                raise LibraryError("Please select one of your active loans.")
