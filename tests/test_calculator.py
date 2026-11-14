from datetime import date
from decimal import Decimal

import pytest

from calculator import (
    filter_by_period,
    get_day_period,
    get_month_period,
    get_week_period,
    get_year_period,
    group_by_category,
    total_expenses,
)
from expense import Expense


@pytest.fixture
def sample_expenses() -> list[Expense]:
    return [
        Expense(amount=Decimal("100.00"), category="їжа", date=date(2026, 11, 1)),
        Expense(
            amount=Decimal("250.50"), category="транспорт", date=date(2026, 11, 15)
        ),
        Expense(amount=Decimal("50.00"), category="їжа", date=date(2026, 11, 30)),
        Expense(amount=Decimal("500.00"), category="оренда", date=date(2026, 12, 1)),
    ]


# --- 1. Тести генерації меж періодів (день, тиждень, місяць, рік) ---


def test_get_day_period() -> None:
    start, end = get_day_period(date(2026, 11, 14))
    assert start == date(2026, 11, 14)
    assert end == date(2026, 11, 15)


def test_get_day_period_month_boundary() -> None:
    start, end = get_day_period(date(2026, 11, 30))
    assert start == date(2026, 11, 30)
    assert end == date(2026, 12, 1)


def test_get_week_period() -> None:
    start, end = get_week_period(date(2026, 11, 9))
    assert start == date(2026, 11, 9)
    assert end == date(2026, 11, 16)


def test_get_week_period_year_rollover() -> None:
    start, end = get_week_period(date(2026, 12, 28))
    assert start == date(2026, 12, 28)
    assert end == date(2027, 1, 4)


def test_get_month_period_regular() -> None:
    start, end = get_month_period(2026, 10)
    assert start == date(2026, 10, 1)
    assert end == date(2026, 11, 1)


def test_get_month_period_december_rollover() -> None:
    start, end = get_month_period(2026, 12)
    assert start == date(2026, 12, 1)
    assert end == date(2027, 1, 1)


def test_get_month_period_leap_year_february() -> None:
    start, end = get_month_period(2028, 2)
    assert start == date(2028, 2, 1)
    assert end == date(2028, 3, 1)


@pytest.mark.parametrize("invalid_month", [0, 13, -1])
def test_get_month_period_invalid_month_raises(invalid_month: int) -> None:
    with pytest.raises(ValueError, match="Місяць має бути"):
        get_month_period(2026, invalid_month)


def test_get_year_period() -> None:
    start, end = get_year_period(2026)
    assert start == date(2026, 1, 1)
    assert end == date(2027, 1, 1)


# --- 2. Тести фільтрації за напіввідкритим інтервалом [start, end) ---


def test_filter_by_period_half_open_boundaries(sample_expenses: list[Expense]) -> None:
    start = date(2026, 11, 1)
    end = date(2026, 12, 1)

    result = filter_by_period(sample_expenses, start, end)

    assert len(result) == 3
    assert all(start <= exp.date < end for exp in result)
    assert date(2026, 12, 1) not in [exp.date for exp in result]


def test_filter_by_period_leap_day_included() -> None:
    leap_expenses = [
        Expense(amount=Decimal("100"), category="кава", date=date(2028, 2, 28)),
        Expense(amount=Decimal("200"), category="книги", date=date(2028, 2, 29)),
        Expense(amount=Decimal("300"), category="їжа", date=date(2028, 3, 1)),
    ]
    start, end = get_month_period(2028, 2)

    result = filter_by_period(leap_expenses, start, end)

    assert len(result) == 2
    assert [exp.date for exp in result] == [date(2028, 2, 28), date(2028, 2, 29)]


def test_filter_by_period_equal_dates_returns_empty(
    sample_expenses: list[Expense],
) -> None:
    same_date = date(2026, 11, 15)
    assert filter_by_period(sample_expenses, same_date, same_date) == []


def test_filter_by_period_start_after_end_raises(
    sample_expenses: list[Expense],
) -> None:
    with pytest.raises(ValueError, match="Дата початку"):
        filter_by_period(sample_expenses, date(2026, 11, 20), date(2026, 11, 10))


def test_filter_by_period_empty_input() -> None:
    assert filter_by_period([], date(2026, 11, 1), date(2026, 12, 1)) == []


# --- 3. Тести підрахунку суми та групування ---


def test_total_expenses_calculates_exact_decimal(
    sample_expenses: list[Expense],
) -> None:
    assert total_expenses(sample_expenses) == Decimal("900.50")


def test_total_expenses_empty_list_returns_zero() -> None:
    result = total_expenses([])
    assert result == Decimal("0")
    assert isinstance(result, Decimal)


def test_group_by_category_empty_list_returns_empty_dict() -> None:
    assert group_by_category([]) == {}


def test_group_by_category_sorting_and_tie_breaking() -> None:
    expenses = [
        Expense(amount=Decimal("200"), category="транспорт", date=date(2026, 11, 1)),
        Expense(amount=Decimal("500"), category="їжа", date=date(2026, 11, 2)),
        Expense(amount=Decimal("300"), category="транспорт", date=date(2026, 11, 3)),
        Expense(amount=Decimal("800"), category="оренда", date=date(2026, 11, 4)),
    ]

    result = group_by_category(expenses)

    assert result == {
        "оренда": Decimal("800"),
        "їжа": Decimal("500"),
        "транспорт": Decimal("500"),
    }
    assert list(result.keys()) == ["оренда", "їжа", "транспорт"]
