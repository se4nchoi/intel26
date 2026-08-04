from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEMO_USERS = (
    ("CARD1001", "Alex Reader", "lib123", True),
    ("CARD1002", "Sam Booker", "book123", False),
)

SEED_BOOKS = (
    ("Pride and Prejudice", "Jane Austen", "9780141439518"),
    ("Frankenstein", "Mary Shelley", "9780141439471"),
    ("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565"),
    ("To Kill a Mockingbird", "Harper Lee", "9780061120084"),
    ("1984", "George Orwell", "9780451524935"),
    ("The Hobbit", "J.R.R. Tolkien", "9780547928227"),
    ("Fahrenheit 451", "Ray Bradbury", "9781451673319"),
    ("The Catcher in the Rye", "J.D. Salinger", "9780316769488"),
    ("The Left Hand of Darkness", "Ursula K. Le Guin", "9780441478125"),
    ("Beloved", "Toni Morrison", "9781400033416"),
    ("The Name of the Rose", "Umberto Eco", "9780544176560"),
    ("The Little Prince", "Antoine de Saint-Exupéry", "9780156012195"),
)


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


class Database:
    def __init__(self, path: str | Path = "library.db") -> None:
        self.path = str(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    card_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash BLOB NOT NULL,
                    password_salt BLOB NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    isbn TEXT NOT NULL UNIQUE,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    book_id INTEGER NOT NULL REFERENCES books(id),
                    borrowed_at TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    returned_at TEXT
                );

                CREATE UNIQUE INDEX IF NOT EXISTS one_active_loan_per_book
                ON loans(book_id) WHERE returned_at IS NULL;
                """
            )

            user_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(users)")
            }
            if "is_admin" not in user_columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0"
                )
                connection.execute(
                    "UPDATE users SET is_admin = 1 WHERE card_id = 'CARD1001'"
                )

            book_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(books)")
            }
            if "is_active" not in book_columns:
                connection.execute(
                    "ALTER TABLE books ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
                )

            if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                for card_id, name, password, is_admin in DEMO_USERS:
                    salt = os.urandom(16)
                    connection.execute(
                        """INSERT INTO users
                           (card_id, name, password_hash, password_salt, is_admin)
                           VALUES (?, ?, ?, ?, ?)""",
                        (card_id, name, hash_password(password, salt), salt, is_admin),
                    )

            if connection.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
                connection.executemany(
                    "INSERT INTO books (title, author, isbn) VALUES (?, ?, ?)",
                    SEED_BOOKS,
                )
