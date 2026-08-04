from __future__ import annotations

import tempfile
import unittest
import sqlite3
from datetime import date
from pathlib import Path

from database import Database
from services import LibraryError, LibraryService


class LibraryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = Database(Path(self.temporary_directory.name) / "test.db")
        database.initialize()
        self.service = LibraryService(database)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_valid_and_invalid_login(self) -> None:
        user = self.service.authenticate("CARD1001", "library123")
        self.assertIsNotNone(user)
        self.assertEqual(user.name, "Alex Reader")
        self.assertTrue(user.is_admin)
        self.assertFalse(self.service.authenticate("CARD1002", "books456").is_admin)
        self.assertIsNone(self.service.authenticate("CARD1001", "wrong"))
        self.assertIsNone(self.service.authenticate("missing", "library123"))

    def test_search_by_title_author_and_isbn(self) -> None:
        self.assertEqual([b["title"] for b in self.service.search_books("hobbit")], ["The Hobbit"])
        self.assertEqual([b["title"] for b in self.service.search_books("Austen")], ["Pride and Prejudice"])
        self.assertEqual([b["title"] for b in self.service.search_books("9780451524935")], ["1984"])

    def test_borrowing_makes_book_unavailable(self) -> None:
        user = self.service.authenticate("CARD1001", "library123")
        book = self.service.search_books("The Hobbit")[0]
        self.service.borrow_book(user.id, book["id"], date(2026, 8, 4))

        self.assertFalse(self.service.search_books("The Hobbit")[0]["available"])
        loan = self.service.active_loans(user.id)[0]
        self.assertEqual(loan["borrowed_at"], "2026-08-04")
        self.assertEqual(loan["due_at"], "2026-08-18")

    def test_unavailable_book_cannot_be_borrowed(self) -> None:
        first = self.service.authenticate("CARD1001", "library123")
        second = self.service.authenticate("CARD1002", "books456")
        book_id = self.service.search_books("1984")[0]["id"]
        self.service.borrow_book(first.id, book_id)
        with self.assertRaisesRegex(LibraryError, "unavailable"):
            self.service.borrow_book(second.id, book_id)

    def test_three_loan_limit(self) -> None:
        user = self.service.authenticate("CARD1001", "library123")
        books = self.service.search_books()
        for book in books[:3]:
            self.service.borrow_book(user.id, book["id"])
        with self.assertRaisesRegex(LibraryError, "three"):
            self.service.borrow_book(user.id, books[3]["id"])

    def test_return_preserves_loan_and_restores_availability(self) -> None:
        user = self.service.authenticate("CARD1001", "library123")
        book = self.service.search_books("Fahrenheit 451")[0]
        self.service.borrow_book(user.id, book["id"], date(2026, 8, 4))
        loan_id = self.service.active_loans(user.id)[0]["id"]
        self.service.return_loan(user.id, loan_id, date(2026, 8, 5))

        self.assertEqual(self.service.active_loans(user.id), [])
        self.assertTrue(self.service.search_books("Fahrenheit 451")[0]["available"])
        with self.service.database.connect() as connection:
            saved = connection.execute("SELECT returned_at FROM loans WHERE id = ?", (loan_id,)).fetchone()
        self.assertEqual(saved["returned_at"], "2026-08-05")

    def test_admin_can_add_update_and_archive_a_book(self) -> None:
        admin = self.service.authenticate("CARD1001", "library123")
        book_id = self.service.add_book(
            admin.id, "  A Wizard of Earthsea  ", " Ursula K. Le Guin ", " 9780547773742 "
        )
        added = self.service.search_books("9780547773742")[0]
        self.assertEqual(added["title"], "A Wizard of Earthsea")
        self.assertEqual(added["author"], "Ursula K. Le Guin")

        self.service.update_book(
            admin.id, book_id, "A Wizard of Earthsea", "Ursula Le Guin", "9780547773742"
        )
        self.assertEqual(self.service.search_books("9780547773742")[0]["author"], "Ursula Le Guin")
        self.assertEqual(self.service.archive_books(admin.id, [book_id]), 1)
        self.assertEqual(self.service.search_books("9780547773742"), [])

    def test_non_admin_cannot_change_catalogue(self) -> None:
        member = self.service.authenticate("CARD1002", "books456")
        book_id = self.service.search_books("The Hobbit")[0]["id"]
        with self.assertRaisesRegex(LibraryError, "Administrator"):
            self.service.add_book(member.id, "Dune", "Frank Herbert", "9780441172719")
        with self.assertRaisesRegex(LibraryError, "Administrator"):
            self.service.update_book(member.id, book_id, "Dune", "Frank Herbert", "9780441172719")
        with self.assertRaisesRegex(LibraryError, "Administrator"):
            self.service.archive_books(member.id, [book_id])

    def test_catalogue_fields_and_isbn_are_validated(self) -> None:
        admin = self.service.authenticate("CARD1001", "library123")
        with self.assertRaisesRegex(LibraryError, "required"):
            self.service.add_book(admin.id, "", "An Author", "123")
        with self.assertRaisesRegex(LibraryError, "ISBN"):
            self.service.add_book(admin.id, "Another Hobbit", "J.R.R. Tolkien", "9780547928227")

    def test_bulk_archive_is_atomic_when_a_book_is_missing(self) -> None:
        admin = self.service.authenticate("CARD1001", "library123")
        books = self.service.search_books()[:2]
        with self.assertRaisesRegex(LibraryError, "no longer exist"):
            self.service.archive_books(admin.id, [books[0]["id"], books[1]["id"], 999999])
        remaining_ids = {book["id"] for book in self.service.search_books()}
        self.assertIn(books[0]["id"], remaining_ids)
        self.assertIn(books[1]["id"], remaining_ids)

    def test_archiving_preserves_and_allows_returning_an_active_loan(self) -> None:
        admin = self.service.authenticate("CARD1001", "library123")
        member = self.service.authenticate("CARD1002", "books456")
        book = self.service.search_books("The Hobbit")[0]
        self.service.borrow_book(member.id, book["id"], date(2026, 8, 4))

        self.service.archive_books(admin.id, [book["id"]])

        self.assertEqual(self.service.search_books("The Hobbit"), [])
        loan = self.service.active_loans(member.id)[0]
        self.assertEqual(loan["title"], "The Hobbit")
        self.service.return_loan(member.id, loan["id"], date(2026, 8, 5))
        self.assertEqual(self.service.active_loans(member.id), [])

    def test_existing_database_is_migrated(self) -> None:
        legacy_path = Path(self.temporary_directory.name) / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    card_id TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash BLOB NOT NULL,
                    password_salt BLOB NOT NULL
                );
                CREATE TABLE books (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    isbn TEXT NOT NULL UNIQUE
                );
                """
            )
        finally:
            connection.close()

        migrated_database = Database(legacy_path)
        migrated_database.initialize()
        migrated_service = LibraryService(migrated_database)
        self.assertTrue(migrated_service.authenticate("CARD1001", "library123").is_admin)
        self.assertEqual(len(migrated_service.search_books()), 12)


if __name__ == "__main__":
    unittest.main()
