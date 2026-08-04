import pytest

from calculator.history import CalculationHistory


def test_history_is_newest_first_and_limited_to_twenty_entries() -> None:
    history = CalculationHistory()
    for value in range(25):
        history.add(f"{value} + 1", str(value + 1))

    assert len(history.entries) == 20
    assert history.entries[0].expression == "24 + 1"
    assert history.entries[-1].expression == "5 + 1"


def test_clear_history() -> None:
    history = CalculationHistory()
    history.add("2 + 2", "4")
    history.clear()

    assert history.entries == ()


def test_history_rejects_incomplete_entries() -> None:
    history = CalculationHistory()
    with pytest.raises(ValueError):
        history.add("", "4")
