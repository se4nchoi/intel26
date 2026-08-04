"""PySide6 Qt Widgets interface for the calculator."""

from __future__ import annotations

from functools import partial

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent, QTextOption
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from calculator.engine import CalculatorEngine, CalculatorError
from calculator.history import CalculationHistory


class WrappingDisplay(QTextEdit):
    """Read-only display that wraps even long unbroken numeric text."""

    def __init__(self, accessible_name: str, maximum_height: int) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(accessible_name)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMaximumHeight(maximum_height)

        text_option = self.document().defaultTextOption()
        text_option.setWrapMode(QTextOption.WrapMode.WrapAnywhere)
        text_option.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.document().setDefaultTextOption(text_option)

    def text(self) -> str:
        """Keep the former QLineEdit-compatible read API used by tests."""
        return self.toPlainText()


class CalculatorWindow(QMainWindow):
    """Windows Calculator-inspired main window."""

    def __init__(self) -> None:
        super().__init__()
        self.engine = CalculatorEngine()
        self.history = CalculationHistory()
        self.theme = "light"

        self.setWindowTitle("Calculator")
        self.setMinimumSize(760, 560)
        self.resize(920, 640)
        self._build_interface()
        self._apply_theme()
        self._refresh_history()
        self._refresh_displays()

        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def _build_interface(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_calculator_panel())
        splitter.addWidget(self._build_history_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([570, 350])
        self.setCentralWidget(splitter)

    def _build_calculator_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("calculatorPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 16, 24)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Standard")
        title.setObjectName("modeTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.theme_button = QPushButton()
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.theme_button.setAccessibleName("Toggle light and dark theme")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.clicked.connect(self._toggle_theme)
        header.addWidget(self.theme_button)
        self.history_toggle_button = QPushButton("Hide history")
        self.history_toggle_button.setObjectName("historyToggleButton")
        self.history_toggle_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.history_toggle_button.setAccessibleName("Toggle history panel")
        self.history_toggle_button.setToolTip("Hide the history panel")
        self.history_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_toggle_button.clicked.connect(self._toggle_history_panel)
        header.addWidget(self.history_toggle_button)
        layout.addLayout(header)

        self.expression_display = WrappingDisplay("Expression", 78)
        self.expression_display.setObjectName("expressionDisplay")
        layout.addWidget(self.expression_display)

        self.result_display = WrappingDisplay("Result", 126)
        self.result_display.setObjectName("resultDisplay")
        layout.addWidget(self.result_display)

        grid = QGridLayout()
        grid.setObjectName("keypadGrid")
        self.keypad_grid = grid
        grid.setSpacing(5)
        rows = [
            [("(", "operator"), (")", "operator"), ("%", "operator"), ("⌫", "clear")],
            [("CE", "clear"), ("C", "clear"), ("mod", "operator"), ("÷", "operator")],
            [("7", "number"), ("8", "number"), ("9", "number"), ("×", "operator")],
            [("4", "number"), ("5", "number"), ("6", "number"), ("−", "operator")],
            [("1", "number"), ("2", "number"), ("3", "number"), ("+", "operator")],
            [("±", "operator"), ("0", "number"), (".", "number"), ("=", "equals")],
        ]

        for row_index, row in enumerate(rows):
            grid.setRowStretch(row_index, 1)
            for column_index, (label, role) in enumerate(row):
                button = QPushButton(label)
                button.setProperty("buttonRole", role)
                button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                button.setMinimumSize(64, 48)
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setAccessibleName(self._accessible_button_name(label))
                button.clicked.connect(partial(self._handle_button, label))
                grid.addWidget(button, row_index, column_index)
            grid.setColumnStretch(row_index % 4, 1)

        for column in range(4):
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid, 1)
        return panel

    def _build_history_panel(self) -> QWidget:
        panel = QFrame()
        self.history_panel = panel
        panel.setObjectName("historyPanel")
        panel.setMinimumWidth(225)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("History")
        title.setObjectName("historyTitle")
        layout.addWidget(title)

        self.empty_history_label = QLabel("There's no history yet")
        self.empty_history_label.setObjectName("emptyHistory")
        self.empty_history_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_history_label.setWordWrap(True)
        layout.addWidget(self.empty_history_label, 1)

        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setWordWrap(True)
        self.history_list.setSpacing(4)
        self.history_list.itemClicked.connect(self._load_history_item)
        layout.addWidget(self.history_list, 1)

        self.clear_history_button = QPushButton("Clear history")
        self.clear_history_button.setObjectName("clearHistoryButton")
        self.clear_history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_history_button.clicked.connect(self._clear_history)
        layout.addWidget(self.clear_history_button)
        return panel

    @staticmethod
    def _accessible_button_name(label: str) -> str:
        names = {
            "⌫": "Backspace",
            "÷": "Divide",
            "×": "Multiply",
            "−": "Subtract",
            "±": "Toggle sign",
            "=": "Equals",
            "%": "Percent",
            "C": "Clear",
            "CE": "Clear entry",
        }
        return names.get(label, label)

    def _handle_button(self, label: str, _checked: bool = False) -> None:
        actions = {
            "(": self.engine.input_left_parenthesis,
            ")": self.engine.input_right_parenthesis,
            "%": self.engine.input_percent,
            "CE": self.engine.clear_entry,
            "C": self.engine.clear,
            "⌫": self.engine.backspace,
            "±": self.engine.toggle_sign,
        }
        if label.isdigit():
            self._perform(self.engine.input_digit, label)
        elif label == ".":
            self._perform(self.engine.input_decimal)
        elif label in {"+", "−", "×", "÷", "mod"}:
            self._perform(self.engine.input_operator, label)
        elif label == "=":
            self._calculate()
        elif label in actions:
            self._perform(actions[label])

    def _perform(self, action: object, *arguments: str) -> None:
        try:
            action(*arguments)  # type: ignore[operator]
        except CalculatorError:
            pass
        self._refresh_displays()

    def _calculate(self) -> None:
        try:
            evaluation = self.engine.evaluate()
        except CalculatorError:
            self._refresh_displays()
            return

        self.history.add(evaluation.expression, evaluation.result)
        self._refresh_history()
        self._refresh_displays()

    def _refresh_displays(self) -> None:
        if self.engine.just_evaluated and self.engine.completed_expression:
            expression_text = f"{self.engine.completed_expression} ="
        else:
            expression_text = self.engine.expression
        self.expression_display.setPlainText(expression_text)
        self.expression_display.setToolTip(expression_text)

        result_text = self.engine.error_message or self.engine.preview()
        self.result_display.setPlainText(result_text)
        self.result_display.setToolTip(result_text)

    def _refresh_history(self) -> None:
        self.history_list.clear()
        for entry in self.history.entries:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry.result)
            item.setSizeHint(QSize(0, 72))
            item.setToolTip(f"Load result {entry.result}")
            self.history_list.addItem(item)

            entry_widget = QFrame()
            entry_widget.setObjectName("historyEntry")
            entry_layout = QVBoxLayout(entry_widget)
            entry_layout.setContentsMargins(10, 7, 10, 7)
            entry_layout.setSpacing(2)

            expression_label = QLabel(f"{entry.expression} =")
            expression_label.setObjectName("historyExpression")
            expression_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            expression_label.setToolTip(entry.expression)
            result_label = QLabel(entry.result)
            result_label.setObjectName("historyResult")
            result_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            result_label.setToolTip(entry.result)
            entry_layout.addWidget(expression_label)
            entry_layout.addWidget(result_label)
            self.history_list.setItemWidget(item, entry_widget)

        has_history = bool(self.history.entries)
        self.history_list.setVisible(has_history)
        self.empty_history_label.setVisible(not has_history)
        self.clear_history_button.setEnabled(has_history)

    def _load_history_item(self, item: QListWidgetItem) -> None:
        result = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(result, str):
            try:
                self.engine.load_result(result)
            except CalculatorError:
                return
            self._refresh_displays()
            self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _clear_history(self) -> None:
        self.history.clear()
        self._refresh_history()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _toggle_history_panel(self, _checked: bool = False) -> None:
        will_show = self.history_panel.isHidden()
        self.history_panel.setVisible(will_show)
        self.history_toggle_button.setText("Hide history" if will_show else "Show history")
        self.history_toggle_button.setToolTip(
            "Hide the history panel" if will_show else "Show the history panel"
        )

    def _toggle_theme(self, _checked: bool = False) -> None:
        self.theme = "dark" if self.theme == "light" else "light"
        self._apply_theme()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API name
        if self.isActiveWindow() and event.type() == QEvent.Type.KeyPress:
            key_event = event  # type: ignore[assignment]
            if self._handle_key_event(key_event):  # type: ignore[arg-type]
                return True
        return super().eventFilter(watched, event)

    def _handle_key_event(self, event: QKeyEvent) -> bool:
        forbidden_modifiers = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier
        if event.modifiers() & forbidden_modifiers:
            return False

        key = event.key()
        text = event.text()
        if len(text) == 1 and text.isdigit():
            self._handle_button(text)
        elif text in {"+", "-", "*", "/", "%", "(", ")", "."}:
            label = {"-": "−", "*": "×", "/": "÷"}.get(text, text)
            self._handle_button(label)
        elif text.lower() == "m":
            self._handle_button("mod")
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) or text == "=":
            self._handle_button("=")
        elif key == Qt.Key.Key_Backspace:
            self._handle_button("⌫")
        elif key == Qt.Key.Key_Escape:
            self._handle_button("C")
        elif key == Qt.Key.Key_Delete:
            self._handle_button("CE")
        else:
            return False
        event.accept()
        return True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API name
        application = QApplication.instance()
        if application is not None:
            application.removeEventFilter(self)
        super().closeEvent(event)

    def _apply_theme(self) -> None:
        if self.theme == "dark":
            colors = {
                "window": "#202020",
                "history": "#1b1b1b",
                "text": "#f5f5f5",
                "muted": "#b5b5b5",
                "border": "#3a3a3a",
                "button": "#323232",
                "number": "#3b3b3b",
                "operator": "#2b2b2b",
                "clear": "#292929",
                "hover": "#454545",
                "pressed": "#505050",
                "accent": "#4cc2ff",
                "accent_hover": "#60c9ff",
                "accent_pressed": "#38a9e6",
                "accent_text": "#10212a",
                "history_hover": "#303030",
                "history_selected": "#23445a",
                "selection": "#315f7d",
            }
            self.theme_button.setText("Dark theme")
        else:
            colors = {
                "window": "#f3f3f3",
                "history": "#f3f3f3",
                "text": "#202020",
                "muted": "#666666",
                "border": "#d6d6d6",
                "button": "#fafafa",
                "number": "#ffffff",
                "operator": "#f7f7f7",
                "clear": "#f0f0f0",
                "hover": "#e9e9e9",
                "pressed": "#dddddd",
                "accent": "#0067c0",
                "accent_hover": "#1975c5",
                "accent_pressed": "#005a9e",
                "accent_text": "#ffffff",
                "history_hover": "#e8e8e8",
                "history_selected": "#d9eaf7",
                "selection": "#8ab4e8",
            }
            self.theme_button.setText("Light theme")

        self.theme_button.setToolTip("Switch to dark theme" if self.theme == "light" else "Switch to light theme")
        self.setStyleSheet(
            f"""
            QMainWindow, QFrame#calculatorPanel {{
                background: {colors['window']};
                color: {colors['text']};
            }}
            QFrame#historyPanel {{
                background: {colors['history']};
                color: {colors['text']};
            }}
            QFrame#historyPanel {{
                border-left: 1px solid {colors['border']};
            }}
            QLabel#modeTitle, QLabel#historyTitle {{
                font-size: 20px;
                font-weight: 600;
                color: {colors['text']};
            }}
            QTextEdit#expressionDisplay, QTextEdit#resultDisplay {{
                border: none;
                background: transparent;
                color: {colors['text']};
                padding: 2px 4px;
                selection-background-color: {colors['selection']};
            }}
            QTextEdit#expressionDisplay {{
                min-height: 30px;
                font-size: 16px;
                color: {colors['muted']};
            }}
            QTextEdit#resultDisplay {{
                min-height: 60px;
                font-size: 38px;
                font-weight: 600;
            }}
            QPushButton {{
                border: 1px solid {colors['border']};
                border-radius: 5px;
                background: {colors['button']};
                color: {colors['text']};
                font-size: 17px;
                padding: 8px;
            }}
            QPushButton:hover {{ background: {colors['hover']}; }}
            QPushButton:pressed {{ background: {colors['pressed']}; }}
            QPushButton[buttonRole="number"] {{
                background: {colors['number']};
                font-weight: 600;
            }}
            QPushButton[buttonRole="operator"] {{ background: {colors['operator']}; }}
            QPushButton[buttonRole="clear"] {{ background: {colors['clear']}; }}
            QPushButton[buttonRole="equals"] {{
                background: {colors['accent']};
                border-color: {colors['accent']};
                color: {colors['accent_text']};
                font-weight: 600;
            }}
            QPushButton[buttonRole="equals"]:hover {{ background: {colors['accent_hover']}; }}
            QPushButton[buttonRole="equals"]:pressed {{ background: {colors['accent_pressed']}; }}
            QPushButton#themeButton, QPushButton#historyToggleButton {{
                min-width: 96px;
                padding: 5px 10px;
                font-size: 13px;
            }}
            QListWidget#historyList {{
                border: none;
                background: transparent;
                outline: none;
                font-size: 15px;
                color: {colors['text']};
            }}
            QListWidget#historyList::item {{
                border-radius: 5px;
                padding: 0;
            }}
            QListWidget#historyList::item:hover {{ background: {colors['history_hover']}; }}
            QListWidget#historyList::item:selected {{
                background: {colors['history_selected']};
                color: {colors['text']};
            }}
            QFrame#historyEntry {{ background: transparent; }}
            QLabel#historyExpression {{ color: {colors['muted']}; font-size: 13px; }}
            QLabel#historyResult {{ color: {colors['text']}; font-size: 18px; font-weight: 600; }}
            QLabel#emptyHistory {{ color: {colors['muted']}; font-size: 14px; }}
            QPushButton#clearHistoryButton {{ font-size: 14px; }}
            QPushButton#clearHistoryButton:disabled {{ color: {colors['muted']}; }}
            QSplitter::handle {{ background: {colors['border']}; width: 1px; }}
            """
        )
