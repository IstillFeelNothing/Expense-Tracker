import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from validator import (
    ValidationError,
    parse_and_validate_amount,
    parse_and_validate_category,
)


class InvalidExpenseDataError(Exception):
    pass


@dataclass(frozen=True)
class Expense:
    amount: Decimal
    category: str
    date: datetime.date
    description: str = ""
    expense_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "amount": str(self.amount),
            "category": self.category,
            "description": self.description,
            "date": self.date.isoformat(),
        }
        if self.expense_id is not None:
            data["id"] = self.expense_id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Expense":
        if not isinstance(data, dict):
            raise InvalidExpenseDataError("Дані витрати повинні бути словником.")

        try:
            if "amount" not in data or "category" not in data or "date" not in data:
                raise InvalidExpenseDataError("Обов'язкові поля відсутні.")

            amount = parse_and_validate_amount(data["amount"])
            category = parse_and_validate_category(data["category"])

            try:
                expense_date = datetime.date.fromisoformat(str(data["date"]))
            except (ValueError, TypeError) as err:
                raise InvalidExpenseDataError(
                    f"Некоректний формат дати: {err}"
                ) from err

            # Обробка опису
            raw_desc = data.get("description", "")
            if raw_desc is None:
                description = ""
            elif isinstance(raw_desc, str):
                description = raw_desc
            else:
                raise InvalidExpenseDataError(
                    f"Опис повинен бути рядком, отримано: {type(raw_desc)}"
                )

            raw_id = data.get("id")
            if raw_id is not None and (type(raw_id) is not int or raw_id < 0):
                raise InvalidExpenseDataError(f"Невалідний ID: {raw_id!r}")

            return cls(
                expense_id=raw_id,
                amount=amount,
                category=category,
                date=expense_date,
                description=description,
            )

        except (ValidationError, KeyError, ValueError, TypeError) as err:
            raise InvalidExpenseDataError(f"Помилка створення Expense: {err}") from err
