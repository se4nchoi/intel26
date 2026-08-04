"""In-memory history for successful calculations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoryEntry:
    expression: str
    result: str


class CalculationHistory:
    """Store newest-first calculation entries with a fixed upper bound."""

    def __init__(self, limit: int = 20) -> None:
        if limit < 1:
            raise ValueError("History limit must be positive")
        self.limit = limit
        self._entries: list[HistoryEntry] = []

    @property
    def entries(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._entries)

    def add(self, expression: str, result: str) -> HistoryEntry:
        if not expression.strip() or not result.strip():
            raise ValueError("History entries require an expression and result")
        entry = HistoryEntry(expression, result)
        self._entries.insert(0, entry)
        del self._entries[self.limit :]
        return entry

    def clear(self) -> None:
        self._entries.clear()
