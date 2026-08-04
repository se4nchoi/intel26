"""Expression evaluation and editable calculator state.

The module intentionally has no Qt dependencies.  Its tokenizer, parser, and
state transitions can therefore be tested in isolation and translated to C++.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException, DivisionByZero, InvalidOperation, localcontext
from enum import Enum, auto
import re


MAX_EXPRESSION_LENGTH = 512
MAX_ABSOLUTE_RESULT = Decimal("1e308")


class CalculatorError(ValueError):
    """Base class for errors that are safe to display to a user."""


class MalformedExpressionError(CalculatorError):
    """Raised when an expression cannot be parsed."""

    def __init__(self, message: str = "Invalid expression") -> None:
        super().__init__(message)


class DivisionByZeroError(CalculatorError):
    """Raised for division or modulo by zero."""

    def __init__(self) -> None:
        super().__init__("Cannot divide by zero")


class ResultOverflowError(CalculatorError):
    """Raised when a result is non-finite or too large for this calculator."""

    def __init__(self) -> None:
        super().__init__("Result is too large")


class ExpressionTooLongError(CalculatorError):
    """Raised when an edit would exceed the configured expression limit."""

    def __init__(self) -> None:
        super().__init__(f"Expression is limited to {MAX_EXPRESSION_LENGTH} characters")


class TokenKind(Enum):
    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    PERCENT = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    END = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    text: str


@dataclass(frozen=True)
class Evaluation:
    expression: str
    result: str


_NUMBER_RE = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_TRAILING_NUMBER_RE = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)$")
_DISPLAY_OPERATORS = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "−": TokenKind.MINUS,
    "*": TokenKind.MULTIPLY,
    "×": TokenKind.MULTIPLY,
    "/": TokenKind.DIVIDE,
    "÷": TokenKind.DIVIDE,
}
_INPUT_OPERATORS = {"+": "+", "-": "−", "−": "−", "*": "×", "×": "×", "/": "÷", "÷": "÷", "mod": "mod"}


def tokenize(expression: str) -> list[Token]:
    """Convert expression text into parser tokens."""
    tokens: list[Token] = []
    index = 0
    while index < len(expression):
        character = expression[index]
        if character.isspace():
            index += 1
            continue

        number_match = _NUMBER_RE.match(expression, index)
        if number_match:
            text = number_match.group(0)
            tokens.append(Token(TokenKind.NUMBER, text))
            index = number_match.end()
            continue

        if expression.startswith("mod", index):
            tokens.append(Token(TokenKind.MODULO, "mod"))
            index += 3
            continue

        if character in _DISPLAY_OPERATORS:
            tokens.append(Token(_DISPLAY_OPERATORS[character], character))
        elif character == "%":
            tokens.append(Token(TokenKind.PERCENT, character))
        elif character == "(":
            tokens.append(Token(TokenKind.LEFT_PAREN, character))
        elif character == ")":
            tokens.append(Token(TokenKind.RIGHT_PAREN, character))
        else:
            raise MalformedExpressionError()
        index += 1

    tokens.append(Token(TokenKind.END, ""))
    return tokens


class _Parser:
    """Small recursive-descent parser implementing normal arithmetic precedence."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    @property
    def current(self) -> Token:
        return self._tokens[self._index]

    def advance(self) -> Token:
        token = self.current
        self._index += 1
        return token

    def parse(self) -> Decimal:
        value = self.parse_expression()
        if self.current.kind is not TokenKind.END:
            raise MalformedExpressionError()
        return value

    def parse_expression(self) -> Decimal:
        value = self.parse_term()
        while self.current.kind in (TokenKind.PLUS, TokenKind.MINUS):
            operator = self.advance().kind
            right = self.parse_term()
            value = value + right if operator is TokenKind.PLUS else value - right
            _ensure_supported_result(value)
        return value

    def parse_term(self) -> Decimal:
        value = self.parse_unary()
        while self.current.kind in (TokenKind.MULTIPLY, TokenKind.DIVIDE, TokenKind.MODULO):
            operator = self.advance().kind
            right = self.parse_unary()
            if operator in (TokenKind.DIVIDE, TokenKind.MODULO) and right == 0:
                raise DivisionByZeroError()
            if operator is TokenKind.MULTIPLY:
                value *= right
            elif operator is TokenKind.DIVIDE:
                value /= right
            else:
                value %= right
            _ensure_supported_result(value)
        return value

    def parse_unary(self) -> Decimal:
        if self.current.kind is TokenKind.PLUS:
            self.advance()
            return self.parse_unary()
        if self.current.kind is TokenKind.MINUS:
            self.advance()
            return -self.parse_unary()
        return self.parse_postfix()

    def parse_postfix(self) -> Decimal:
        value = self.parse_primary()
        while self.current.kind is TokenKind.PERCENT:
            self.advance()
            value /= Decimal(100)
        return value

    def parse_primary(self) -> Decimal:
        if self.current.kind is TokenKind.NUMBER:
            text = self.advance().text
            try:
                return Decimal(text)
            except InvalidOperation as error:
                raise MalformedExpressionError() from error

        if self.current.kind is TokenKind.LEFT_PAREN:
            self.advance()
            value = self.parse_expression()
            if self.current.kind is not TokenKind.RIGHT_PAREN:
                raise MalformedExpressionError("Missing closing parenthesis")
            self.advance()
            return value

        raise MalformedExpressionError()


def _ensure_supported_result(value: Decimal) -> None:
    if not value.is_finite() or abs(value) > MAX_ABSOLUTE_RESULT:
        raise ResultOverflowError()


def evaluate_expression(expression: str) -> Decimal:
    """Evaluate an arithmetic expression without using Python ``eval``."""
    if not expression.strip():
        raise MalformedExpressionError()
    try:
        with localcontext() as context:
            context.prec = 28
            value = _Parser(tokenize(expression)).parse()
            _ensure_supported_result(value)
            return value
    except CalculatorError:
        raise
    except DivisionByZero as error:
        raise DivisionByZeroError() from error
    except DecimalException as error:
        raise ResultOverflowError() from error


def format_decimal(value: Decimal) -> str:
    """Format a Decimal without insignificant trailing zeroes or negative zero."""
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


class CalculatorEngine:
    """Own the editable expression and calculator input transitions."""

    def __init__(self, max_length: int = MAX_EXPRESSION_LENGTH) -> None:
        self.max_length = max_length
        self.expression = ""
        self.completed_expression = ""
        self.just_evaluated = False
        self.error_message = ""

    def _set_expression(self, value: str) -> None:
        if len(value) > self.max_length:
            error = ExpressionTooLongError()
            self.error_message = str(error)
            raise error
        self.expression = value
        self.error_message = ""

    def _prepare_for_value(self) -> None:
        if self.just_evaluated:
            self.clear()
        self.just_evaluated = False

    def input_digit(self, digit: str) -> None:
        if len(digit) != 1 or not digit.isdigit():
            raise ValueError("input_digit expects one digit")
        self._prepare_for_value()

        if self.expression.endswith((")", "%")):
            self._set_expression(f"{self.expression} × {digit}")
            return

        match = _TRAILING_NUMBER_RE.search(self.expression)
        if match and match.group(0) == "0":
            self._set_expression(self.expression[: match.start()] + digit)
        else:
            self._set_expression(self.expression + digit)

    def input_decimal(self) -> None:
        self._prepare_for_value()
        if self.expression.endswith((")", "%")):
            self._set_expression(self.expression + " × 0.")
            return
        match = _TRAILING_NUMBER_RE.search(self.expression)
        if match and "." in match.group(0):
            return
        self._set_expression(self.expression + ("." if match else "0."))

    def input_operator(self, operator: str) -> None:
        try:
            display_operator = _INPUT_OPERATORS[operator]
        except KeyError as error:
            raise ValueError(f"Unknown operator: {operator}") from error

        self.error_message = ""
        self.just_evaluated = False
        if not self.expression:
            if display_operator == "−":
                self._set_expression("-")
            return

        stripped = self.expression.rstrip()
        if stripped.endswith("("):
            if display_operator == "−":
                self._set_expression(stripped + "-")
            return

        trailing_operator = re.search(r"\s(?:\+|−|×|÷|mod)\s*$", self.expression)
        if trailing_operator:
            self._set_expression(self.expression[: trailing_operator.start()] + f" {display_operator} ")
            return

        if stripped == "-":
            return
        self._set_expression(stripped + f" {display_operator} ")

    def input_left_parenthesis(self) -> None:
        self._prepare_for_value()
        if self.expression and (self.expression[-1].isdigit() or self.expression.endswith((")", "%"))):
            self._set_expression(self.expression + " × (")
        else:
            self._set_expression(self.expression + "(")

    def input_right_parenthesis(self) -> None:
        self.just_evaluated = False
        stripped = self.expression.rstrip()
        if (
            stripped
            and stripped.count("(") > stripped.count(")")
            and (stripped[-1].isdigit() or stripped.endswith((")", "%")))
        ):
            self._set_expression(stripped + ")")

    def input_percent(self) -> None:
        self.just_evaluated = False
        stripped = self.expression.rstrip()
        if stripped and (stripped[-1].isdigit() or stripped.endswith((")", "%"))):
            self._set_expression(stripped + "%")

    def backspace(self) -> None:
        if self.just_evaluated or self.error_message:
            self.clear()
            return
        stripped = self.expression.rstrip()
        if stripped:
            self._set_expression(stripped[:-1].rstrip())

    def clear_entry(self) -> None:
        if self.just_evaluated or self.error_message:
            self.clear()
            return
        stripped = self.expression.rstrip()
        percent_suffix = len(stripped) - len(stripped.rstrip("%"))
        without_percent = stripped.rstrip("%")
        match = _TRAILING_NUMBER_RE.search(without_percent)
        if match:
            self._set_expression(without_percent[: match.start()])
        elif percent_suffix:
            self._set_expression(without_percent)

    def clear(self) -> None:
        self.expression = ""
        self.completed_expression = ""
        self.just_evaluated = False
        self.error_message = ""

    def toggle_sign(self) -> None:
        self._prepare_for_value()
        match = _TRAILING_NUMBER_RE.search(self.expression.rstrip("%"))
        if not match:
            return

        start = match.start()
        if start > 0 and self.expression[start - 1] == "-":
            minus_index = start - 1
            prefix = self.expression[:minus_index].rstrip()
            if not prefix or prefix.endswith(("(", "+", "−", "×", "÷", "mod")):
                self._set_expression(self.expression[:minus_index] + self.expression[start:])
                return
        self._set_expression(self.expression[:start] + "-" + self.expression[start:])

    def evaluate(self) -> Evaluation:
        original = self.expression.strip()
        try:
            result = format_decimal(evaluate_expression(original))
        except CalculatorError as error:
            self.error_message = str(error)
            self.just_evaluated = False
            raise

        self.completed_expression = original
        self.expression = result
        self.error_message = ""
        self.just_evaluated = True
        return Evaluation(original, result)

    def load_result(self, result: str) -> None:
        """Load a successful history result as the next expression."""
        evaluate_expression(result)
        self._set_expression(result)
        self.completed_expression = ""
        self.just_evaluated = True

    def preview(self) -> str:
        """Return a live result when valid, otherwise the current numeric entry."""
        if not self.expression:
            return "0"
        try:
            return format_decimal(evaluate_expression(self.expression))
        except CalculatorError:
            matches = list(_NUMBER_RE.finditer(self.expression))
            return matches[-1].group(0) if matches else "0"
