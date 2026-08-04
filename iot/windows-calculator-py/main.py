"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from calculator.window import CalculatorWindow


def main() -> int:
    """Start the Qt application."""
    app = QApplication(sys.argv)
    window = CalculatorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
