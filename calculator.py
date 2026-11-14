from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

from expense import Expense

UKRAINIAN_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
CHAR_ORDER = {char: idx for idx, char in enumerate(UKRAINIAN_ALPHABET)}


def _ukrainian_sort_key(text: str) -> tuple[int, ...]:
    return tuple(CHAR_ORDER.get(ch, ord(ch) + 1000) for ch in text.lower())


def get_day_period(day: date) -> tuple[date, date]:
    return day, day + timedelta(days=1)


def get_week_period(week_start: date) -> tuple[date, date]:
    return week_start, week_start + timedelta(days=7)


def get_month_period(year: int, month: int) -> tuple[date, date]:
    if not 1 <= month <= 12:
        raise ValueError(f"Місяць має бути в діапазоні 1..12, отримано: {month}")

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    return start, end


def get_year_period(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year + 1, 1, 1)


def filter_by_period(
    expenses: Iterable[Expense],
    start: date,
    end: date,
) -> list[Expense]:
    if start > end:
        raise ValueError(
            f"Дата початку ({start}) не може бути пізнішою за дату кінця ({end})"
        )

    return [expense for expense in expenses if start <= expense.date < end]


def total_expenses(expenses: Iterable[Expense]) -> Decimal:
    return sum((expense.amount for expense in expenses), start=Decimal("0"))


def group_by_category(expenses: Iterable[Expense]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for expense in expenses:
        totals[expense.category] += expense.amount

    sorted_items = sorted(
        totals.items(),
        key=lambda item: (-item[1], _ukrainian_sort_key(item[0])),
    )
    return dict(sorted_items)
