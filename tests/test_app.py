from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app import ExpenseApp
from expense import Expense
from repository import ExpenseRepository
from storage_protocol import StorageError
from tests.fakes import FakeStorage
from view import ConsoleView


def test_app_end_to_end_add_expense_persists_in_repository() -> None:
    storage = FakeStorage()
    repo = ExpenseRepository(storage)
    fixed_today = date(2026, 11, 14)

    inputs = iter(["1", "250.50", "Їжа", "", "Обід", "0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view, today_fn=lambda: fixed_today)
    app.run()

    saved_items = repo.get_all()
    assert len(saved_items) == 1
    assert saved_items[0].expense_id == 1
    assert saved_items[0].amount == Decimal("250.50")
    assert saved_items[0].category == "їжа"
    assert saved_items[0].date == fixed_today
    assert saved_items[0].description == "Обід"
    assert len(storage.save_calls) == 1


def test_app_end_to_end_edit_expense_partial_update() -> None:
    storage = FakeStorage()
    repo = ExpenseRepository(storage)
    repo.load()
    created = repo.add(
        Expense(
            amount=Decimal("100.00"),
            category="транспорт",
            date=date(2026, 11, 10),
            description="Метро",
        )
    )

    inputs = iter(["3", str(created.expense_id), "150", "", "", "Таксі", "0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view, today_fn=lambda: date(2026, 11, 14))
    app.run()

    assert created.expense_id is not None
    updated = repo.get_by_id(created.expense_id)
    assert updated is not None
    assert updated.amount == Decimal("150")
    assert updated.category == "транспорт"
    assert updated.date == date(2026, 11, 10)
    assert updated.description == "Таксі"


def test_app_edit_nonexistent_id_shows_error() -> None:
    storage = FakeStorage()
    repo = ExpenseRepository(storage)
    repo.load()
    repo.add(
        Expense(
            amount=Decimal("100.00"),
            category="їжа",
            date=date(2026, 11, 10),
        )
    )

    inputs = iter(["3", "999", "0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view)
    app.run()

    assert any("не знайдено" in line.lower() for line in outputs)


def test_app_startup_with_corrupted_storage_creates_backup_and_continues() -> None:
    backup = Path("fake_corrupted_backup.json")
    storage = FakeStorage(corrupted_once_backup=backup)
    repo = ExpenseRepository(storage)

    inputs = iter(["0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view)
    app.run()

    rendered = "\n".join(outputs)
    assert "пошкоджено" in rendered.lower()
    assert backup.name in rendered
    assert "до зустрічі" in rendered.lower()


def test_app_startup_without_backup_exits_immediately() -> None:
    storage = FakeStorage(load_error=StorageError("Немає доступу до файлу"))
    repo = ExpenseRepository(storage)

    def fail_if_called(_: str) -> str:
        pytest.fail("input() не мав викликатися при критичній помилці старту")

    outputs: list[str] = []
    view = ConsoleView(input_fn=fail_if_called, output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view)
    app.run()

    assert any("немає доступу" in line.lower() for line in outputs)


def test_app_handles_save_error_without_crashing() -> None:
    storage = FakeStorage(save_error=StorageError("Диск переповнений"))
    repo = ExpenseRepository(storage)

    inputs = iter(["1", "200", "їжа", "", "", "0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view)
    app.run()

    assert repo.get_all() == []
    assert any("диск переповнений" in line.lower() for line in outputs)


def test_app_end_to_end_edit_expense_clears_description_with_dash() -> None:
    storage = FakeStorage()
    repo = ExpenseRepository(storage)
    repo.load()
    created = repo.add(
        Expense(
            amount=Decimal("100.00"),
            category="їжа",
            date=date(2026, 11, 10),
            description="Зайвий опис",
        )
    )

    inputs = iter(["3", str(created.expense_id), "", "", "", "-", "0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view, today_fn=lambda: date(2026, 11, 14))
    app.run()

    assert created.expense_id is not None
    updated = repo.get_by_id(created.expense_id)
    assert updated is not None
    assert updated.description == ""


def test_app_end_to_end_delete_expense_removes_from_repository() -> None:
    storage = FakeStorage()
    repo = ExpenseRepository(storage)
    repo.load()
    first = repo.add(
        Expense(amount=Decimal("50.00"), category="кава", date=date(2026, 11, 14))
    )
    second = repo.add(
        Expense(amount=Decimal("200.00"), category="їжа", date=date(2026, 11, 14))
    )

    inputs = iter(["4", str(first.expense_id), "0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view)
    app.run()

    remaining = repo.get_all()
    assert len(remaining) == 1
    assert remaining[0].expense_id == second.expense_id
    assert any("видалено" in line.lower() for line in outputs)


def test_app_stats_today_and_week_use_injected_today_fn() -> None:
    storage = FakeStorage()
    repo = ExpenseRepository(storage)
    repo.load()

    fixed_today = date(2026, 11, 14)
    repo.add(Expense(amount=Decimal("100.00"), category="їжа", date=date(2026, 11, 14)))
    repo.add(
        Expense(amount=Decimal("250.00"), category="транспорт", date=date(2026, 11, 8))
    )
    repo.add(Expense(amount=Decimal("999.00"), category="одяг", date=date(2026, 11, 1)))

    inputs = iter(["5", "6", "0"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    app = ExpenseApp(repo=repo, view=view, today_fn=lambda: fixed_today)
    app.run()

    rendered = "\n".join(outputs)
    assert "Витрати за 14.11.2026" in rendered
    assert "100,00\u00a0грн" in rendered
    assert "Витрати за 7 днів (08.11.2026 – 14.11.2026)" in rendered
    assert "350,00\u00a0грн" in rendered
    assert "999,00\u00a0грн" not in rendered
