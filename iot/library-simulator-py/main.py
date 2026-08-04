from pathlib import Path

from database import Database
from services import LibraryService
from ui import run_application


def main() -> int:
    database = Database(Path(__file__).resolve().parent / "library.db")
    database.initialize()
    return run_application(LibraryService(database))


if __name__ == "__main__":
    raise SystemExit(main())
