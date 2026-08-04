import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextOption
from PySide6.QtWidgets import QApplication, QPushButton

from calculator.window import CalculatorWindow


@pytest.fixture(scope="module")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(application: QApplication) -> CalculatorWindow:
    calculator_window = CalculatorWindow()
    yield calculator_window
    calculator_window.close()


def test_wrapping_history_toggle_pointer_cursors_and_keypad_order(
    window: CalculatorWindow, application: QApplication
) -> None:
    window.show()
    application.processEvents()

    assert window.expression_display.document().defaultTextOption().wrapMode() == QTextOption.WrapMode.WrapAnywhere
    assert window.result_display.document().defaultTextOption().wrapMode() == QTextOption.WrapMode.WrapAnywhere
    assert window.expression_display.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert window.result_display.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded

    expected_rows = [
        ["(", ")", "%", "⌫"],
        ["CE", "C", "mod", "÷"],
    ]
    for row_index, expected_row in enumerate(expected_rows):
        actual_row = [window.keypad_grid.itemAtPosition(row_index, column).widget().text() for column in range(4)]
        assert actual_row == expected_row

    for button in window.findChildren(QPushButton):
        assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor

    assert window.history_panel.isVisibleTo(window)
    assert window.history_toggle_button.text() == "Hide history"
    window.history_toggle_button.click()
    assert not window.history_panel.isVisible()
    assert window.history_toggle_button.text() == "Show history"
    window.history_toggle_button.click()
    assert window.history_panel.isVisibleTo(window)
    assert window.history_toggle_button.text() == "Hide history"


def test_buttons_calculate_and_record_successful_history(window: CalculatorWindow) -> None:
    for label in ("2", "+", "3", "×", "4", "="):
        window._handle_button(label)

    assert window.result_display.text() == "14"
    assert len(window.history.entries) == 1
    assert window.history.entries[0].expression == "2 + 3 × 4"
    assert window.history_list.count() == 1
    history_item = window.history_list.item(0)
    assert history_item.sizeHint().height() == 72
    assert window.history_list.itemWidget(history_item) is not None


def test_invalid_calculation_is_not_recorded(window: CalculatorWindow) -> None:
    for label in ("8", "÷", "0", "="):
        window._handle_button(label)

    assert window.result_display.text() == "Cannot divide by zero"
    assert window.history.entries == ()


def test_keyboard_input_reaches_engine(window: CalculatorWindow) -> None:
    key_events = [
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_7, Qt.KeyboardModifier.NoModifier, "7"),
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Plus, Qt.KeyboardModifier.NoModifier, "+"),
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_5, Qt.KeyboardModifier.NoModifier, "5"),
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier, ""),
    ]
    for event in key_events:
        assert window._handle_key_event(event)

    assert window.result_display.text() == "12"


def test_history_item_loads_result_and_clear_history_empties_list(window: CalculatorWindow) -> None:
    for label in ("6", "×", "7", "="):
        window._handle_button(label)

    item = window.history_list.item(0)
    window._load_history_item(item)
    window._handle_button("+")
    window._handle_button("8")
    window._handle_button("=")

    assert window.result_display.text() == "50"
    window._clear_history()
    assert window.history.entries == ()
    assert window.history_list.count() == 0
    assert window.empty_history_label.isVisibleTo(window)


def test_theme_button_switches_between_dark_and_light(window: CalculatorWindow) -> None:
    assert window.theme == "light"
    assert window.theme_button.text() == "Light theme"

    window.theme_button.click()
    assert window.theme == "dark"
    assert window.theme_button.text() == "Dark theme"
    assert "#202020" in window.styleSheet()

    window.theme_button.click()
    assert window.theme == "light"
    assert "#f3f3f3" in window.styleSheet()
