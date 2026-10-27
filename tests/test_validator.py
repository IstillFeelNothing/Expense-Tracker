from decimal import Decimal

import pytest

from validator import ValidationError, parse_and_validate_amount


@pytest.mark.parametrize(
    "input_str, expected_output",
    [
        ("50.50", Decimal("50.50")),
        ("0.01", Decimal("0.01")),
        ("100", Decimal(100)),
        ("  50  ", Decimal(50)),
        ("1000000", Decimal(1000000)),
        ("050", Decimal(50)),
        ("50,50", Decimal("50.50")),
    ]
)
def test_parse_and_validate_amount_success(input_str: str, expected_output: Decimal):
    assert parse_and_validate_amount(input_str) == expected_output

@pytest.mark.parametrize(
    "input_str, error_message",
    [
        ("-50", "Сума витрати має бути більшою за 0."),
        ("abc", "Некоректний формат числа"),
        ("", "Сума витрати не може бути порожньою."),
        ("100.123", "Сума витрати не може мати більше двох знаків після коми."),
        ("1e3", "Експоненціальний запис не підтримується"),
        ("Infinity", "Сума витрати не може бути нескінченной."),
        ("NaN", "Не є числом NaN."),
        ("1000000.01", "Сума витрати перевищує максимально допустиме значення 1000000.00."),
        ("0", "Сума витрати має бути більшою за 0."),
    ],
)
def test_parse_and_validate_amount_invalid(input_str: str, error_message: str):
    with pytest.raises(ValidationError, match=error_message):
        parse_and_validate_amount(input_str)

def test_parse_and_validate_amount_wrong_type():
    with pytest.raises(TypeError, match="Потрібно передати рядок, що представляє число."):
        parse_and_validate_amount(None)