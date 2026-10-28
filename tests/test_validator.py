from decimal import Decimal
import datetime
import re

import pytest

from validator import (
    ValidationError,
    parse_and_validate_amount,
    parse_and_validate_date,
)


FIXED_TODAY = datetime.date(2026, 10, 28)
INCORRECT_DATE_FORMAT_ERROR = (
    "Некоректний формат або значення дати. Очікується YYYY-MM-DD або DD.MM.YYYY."
)


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
    ],
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
        ("Infinity", "Сума витрати не може бути нескінченною."),
        ("NaN", "Не є числом NaN."),
        (
            "1000000.01",
            "Сума витрати перевищує максимально допустиме значення 1000000.00.",
        ),
        ("0", "Сума витрати має бути більшою за 0."),
    ],
)
def test_parse_and_validate_amount_invalid(input_str: str, error_message: str):
    with pytest.raises(ValidationError, match=re.escape(error_message)):
        parse_and_validate_amount(input_str)


def test_parse_and_validate_amount_wrong_type():
    with pytest.raises(
        TypeError, match="Потрібно передати рядок, що представляє число."
    ):
        parse_and_validate_amount(None)


@pytest.mark.parametrize(
    "input_str, expected_output",
    [
        ("2023-01-01", datetime.date(2023, 1, 1)),
        ("01.01.2023", datetime.date(2023, 1, 1)),
        ("2023-1-1", datetime.date(2023, 1, 1)),
        ("1.1.2023", datetime.date(2023, 1, 1)),
        (" 01.01.2023 ", datetime.date(2023, 1, 1)),
        ("", FIXED_TODAY),
        ("28.10.2026", FIXED_TODAY),
        ("28.10.1926", datetime.date(1926, 10, 28)),
    ],
)
def test_parse_and_validate_date_success(
    input_str: str, expected_output: datetime.date
):
    assert parse_and_validate_date(input_str, today=FIXED_TODAY) == expected_output


@pytest.mark.parametrize(
    "input_str, error_message",
    [
        (
            "01.01.23",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        (
            "2023-13-01",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        (
            "01.13.2023",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        (
            "31.02.2026",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        (
            "2026-02-31",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        (
            "29.02.2025",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        (
            "27/10/2026",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        (
            "abc",
            INCORRECT_DATE_FORMAT_ERROR,
        ),
        ("29.10.2026", "Дата не може бути в майбутньому."),
        ("27.10.1926", "Дата не може бути старішою за 100 років."),
    ],
)
def test_parse_and_validate_date_invalid(input_str: str, error_message: str):
    with pytest.raises(ValidationError, match=re.escape(error_message)):
        parse_and_validate_date(input_str, today=FIXED_TODAY)


def test_parse_and_validate_date_wrong_type():
    with pytest.raises(
        TypeError, match="Потрібно передати рядок, що представляє дату."
    ):
        parse_and_validate_date(None)
