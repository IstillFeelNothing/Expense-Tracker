import dataclasses
import datetime
from decimal import Decimal
from typing import Any

import pytest

from expense import Expense, InvalidExpenseDataError


def test_expense_to_dict_converts_decimal_and_date_to_strings() -> None:
    exp = Expense(
        expense_id=1,
        amount=Decimal("150.50"),
        category="харчування",
        date=datetime.date(2026, 10, 30),
        description="обід",
    )

    data = exp.to_dict()

    assert data == {
        "id": 1,
        "amount": "150.50",
        "category": "харчування",
        "date": "2026-10-30",
        "description": "обід",
    }


def test_expense_to_dict_omits_id_when_none() -> None:
    exp = Expense(
        amount=Decimal("20.00"),
        category="транспорт",
        date=datetime.date(2026, 10, 30),
    )

    data = exp.to_dict()

    assert "id" not in data
    assert data["amount"] == "20.00"


def test_expense_from_dict_valid_data() -> None:
    raw_data = {
        "id": 42,
        "amount": "99.99",
        "category": "книги",
        "date": "2026-10-30",
        "description": "Python Clean Code",
    }

    exp = Expense.from_dict(raw_data)

    assert exp.expense_id == 42
    assert exp.amount == Decimal("99.99")
    assert exp.category == "книги"
    assert exp.date == datetime.date(2026, 10, 30)
    assert exp.description == "Python Clean Code"


def test_expense_supports_dataclasses_replace_and_hash() -> None:
    """Перевірка підтримки replace() та хешування."""
    exp = Expense(
        expense_id=1,
        amount=Decimal("100.00"),
        category="їжа",
        date=datetime.date(2026, 10, 30),
    )

    updated_exp = dataclasses.replace(exp, amount=Decimal("200.00"))
    assert updated_exp.amount == Decimal("200.00")
    assert updated_exp.expense_id == 1

    # Об'єкт можна додавати в set/dict завдяки __hash__
    expense_set = {exp, updated_exp}
    assert len(expense_set) == 2


@pytest.mark.parametrize("expense_id", [10, None])
def test_expense_round_trip(expense_id: int | None) -> None:
    """Expense.from_dict(e.to_dict()) == e."""
    original = Expense(
        expense_id=expense_id,
        amount=Decimal("250.75"),
        category="продукти",
        date=datetime.date(2026, 10, 28),
        description="супермаркет",
    )

    serialized = original.to_dict()
    restored = Expense.from_dict(serialized)

    assert restored == original


def test_expense_is_immutable() -> None:
    exp = Expense(
        expense_id=1,
        amount=Decimal("10.00"),
        category="кава",
        date=datetime.date(2026, 10, 30),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        exp.amount = Decimal("20.00")  # type: ignore


@pytest.mark.parametrize(
    "invalid_data",
    [
        "not a dict",
        {"category": "їжа", "date": "2026-10-30"},
        {"amount": "100.00", "date": "2026-10-30"},
        {"amount": "100.00", "category": "їжа"},
        {"amount": "invalid_number", "category": "їжа", "date": "2026-10-30"},
        {"amount": True, "category": "їжа", "date": "2026-10-30"},
        {"amount": "-50.00", "category": "їжа", "date": "2026-10-30"},
        {"amount": "0.00", "category": "їжа", "date": "2026-10-30"},
        {"amount": "10.00", "category": 123, "date": "2026-10-30"},
        {"amount": "10.00", "category": None, "date": "2026-10-30"},
        {"amount": "10.00", "category": "їжа", "date": "invalid-date"},
        {"amount": "10.00", "category": "їжа", "date": "2026-10-30", "id": "abc"},
        {"amount": "10.00", "category": "їжа", "date": "2026-10-30", "id": -1},
        {
            "amount": "10.00",
            "category": "їжа",
            "date": "2026-10-30",
            "description": 123,
        },
    ],
)
def test_from_dict_raises_invalid_expense_data_error(invalid_data: Any) -> None:
    with pytest.raises(InvalidExpenseDataError):
        Expense.from_dict(invalid_data)
