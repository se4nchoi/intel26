from decimal import Decimal

import pytest

from calculator.engine import (
    CalculatorEngine,
    DivisionByZeroError,
    ExpressionTooLongError,
    MalformedExpressionError,
    ResultOverflowError,
    evaluate_expression,
    format_decimal,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 × 4", "14"),
        ("(2 + 3) × 4", "20"),
        ("1.5 + 2.25", "3.75"),
        ("-5 + 2", "-3"),
        ("10%", "0.1"),
        ("17 mod 5", "2"),
        ("1 + 2 ÷ 3 + 2 × 10", "21.66666666666666666666666667"),
    ],
)
def test_evaluate_expression(expression: str, expected: str) -> None:
    assert format_decimal(evaluate_expression(expression)) == expected


def test_division_by_zero_has_friendly_error() -> None:
    with pytest.raises(DivisionByZeroError, match="Cannot divide by zero"):
        evaluate_expression("10 ÷ 0")


@pytest.mark.parametrize("expression", ["2 +", "((2)", "2 3", "hello"])
def test_malformed_expression(expression: str) -> None:
    with pytest.raises(MalformedExpressionError):
        evaluate_expression(expression)


def test_result_overflow() -> None:
    huge_number = "1" + ("0" * 308)
    with pytest.raises(ResultOverflowError, match="too large"):
        evaluate_expression(f"{huge_number} × 10")


def test_repeated_operator_replaces_previous_operator() -> None:
    engine = CalculatorEngine()
    engine.input_digit("2")
    engine.input_operator("+")
    engine.input_operator("×")
    engine.input_digit("3")

    assert engine.expression == "2 × 3"
    assert engine.evaluate().result == "6"


def test_decimal_point_is_limited_to_one_per_number() -> None:
    engine = CalculatorEngine()
    for key in ("1", ".", "2", ".", "3"):
        engine.input_decimal() if key == "." else engine.input_digit(key)

    assert engine.expression == "1.23"


def test_backspace_removes_last_character() -> None:
    engine = CalculatorEngine()
    engine.input_digit("1")
    engine.input_digit("2")
    engine.input_digit("3")
    engine.backspace()

    assert engine.expression == "12"


def test_clear_entry_removes_only_current_number() -> None:
    engine = CalculatorEngine()
    for digit in "12":
        engine.input_digit(digit)
    engine.input_operator("+")
    for digit in "345":
        engine.input_digit(digit)

    engine.clear_entry()
    engine.input_digit("7")

    assert engine.expression == "12 + 7"


def test_toggle_sign_of_current_number() -> None:
    engine = CalculatorEngine()
    engine.input_digit("8")
    engine.input_operator("+")
    engine.input_digit("3")
    engine.toggle_sign()

    assert engine.expression == "8 + -3"
    assert engine.evaluate().result == "5"


def test_number_after_equals_starts_new_expression() -> None:
    engine = CalculatorEngine()
    engine.input_digit("2")
    engine.input_operator("+")
    engine.input_digit("3")
    engine.evaluate()
    engine.input_digit("9")

    assert engine.expression == "9"


def test_operator_after_equals_continues_from_result() -> None:
    engine = CalculatorEngine()
    engine.input_digit("2")
    engine.input_operator("+")
    engine.input_digit("3")
    engine.evaluate()
    engine.input_operator("×")
    engine.input_digit("4")

    assert engine.evaluate().result == "20"


def test_expression_length_is_enforced_without_mutation() -> None:
    engine = CalculatorEngine(max_length=3)
    for digit in "123":
        engine.input_digit(digit)

    with pytest.raises(ExpressionTooLongError):
        engine.input_digit("4")

    assert engine.expression == "123"


def test_parenthesis_buttons_and_implicit_multiplication() -> None:
    engine = CalculatorEngine()
    engine.input_digit("2")
    engine.input_left_parenthesis()
    engine.input_digit("3")
    engine.input_operator("+")
    engine.input_digit("4")
    engine.input_right_parenthesis()

    assert engine.expression == "2 × (3 + 4)"
    assert engine.evaluate().result == "14"


def test_decimal_formatter_removes_negative_zero() -> None:
    assert format_decimal(Decimal("-0.000")) == "0"
