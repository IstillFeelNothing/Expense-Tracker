import datetime
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from expense import Expense
from json_storage import JSONStorage
from repository import (
    ExpenseNotFoundError,
    ExpenseRepository,
    RepositoryError,
    RepositoryLoadError,
    RepositoryNotInitializedError,
    RepositorySaveError,
)
from storage_protocol import CorruptedStorageError, StorageData, StorageError


class FakeStorage:
    def __init__(
        self,
        initial_data: StorageData | None = None,
        load_error: Exception | None = None,
        save_error: StorageError | None = None,
    ) -> None:
        self.data: StorageData = initial_data or {"last_id": 0, "expenses": []}
        self.load_error = load_error
        self.save_error = save_error
        self.save_calls: list[StorageData] = []
        self.backup_called: bool = False

    def load(self) -> StorageData:
        if self.load_error is not None:
            raise self.load_error
        return self.data

    def save(self, data: StorageData) -> None:
        if self.save_error is not None:
            raise self.save_error
        self.data = data
        self.save_calls.append(data)

    def backup_corrupted_data(self) -> Path:
        self.backup_called = True
        return Path("fake_backup.json")


@pytest.fixture
def sample_raw_data() -> StorageData:
    return {
        "last_id": 2,
        "expenses": [
            {
                "id": 1,
                "amount": "150.50",
                "category": "їжа",
                "description": "Обід",
                "date": "2026-11-10",
            },
            {
                "id": 2,
                "amount": "45.00",
                "category": "транспорт",
                "description": "Метро",
                "date": "2026-11-11",
            },
        ],
    }


def make_expense(
    expense_id: int | None = None,
    amount: str = "100.00",
    category: str = "їжа",
    description: str = "Кава",
    expense_date: datetime.date = datetime.date(2026, 11, 12),
) -> Expense:
    return Expense(
        amount=Decimal(amount),
        category=category,
        date=expense_date,
        description=description,
        expense_id=expense_id,
    )


def test_methods_raise_before_load() -> None:
    storage = FakeStorage()
    repo = ExpenseRepository(storage)
    expense = make_expense()

    assert issubclass(RepositoryNotInitializedError, RuntimeError)
    assert not issubclass(RepositoryNotInitializedError, RepositoryError)

    with pytest.raises(RepositoryNotInitializedError):
        repo.get_all()

    with pytest.raises(RepositoryNotInitializedError):
        repo.get_by_id(1)

    with pytest.raises(RepositoryNotInitializedError):
        repo.add(expense)

    with pytest.raises(RepositoryNotInitializedError):
        repo.update(replace(expense, expense_id=1))

    with pytest.raises(RepositoryNotInitializedError):
        repo.delete(1)


def test_load_restores_expenses_and_last_id() -> None:
    raw_data: StorageData = {
        "last_id": 5,
        "expenses": [
            {
                "id": 1,
                "amount": "50.00",
                "category": "їжа",
                "description": "Чай",
                "date": "2026-11-01",
            },
            {
                "id": 2,
                "amount": "120.00",
                "category": "транспорт",
                "description": "Таксі",
                "date": "2026-11-02",
            },
        ],
    }
    storage = FakeStorage(initial_data=raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    added = repo.add(make_expense())

    assert len(repo.get_all()) == 3
    assert added.expense_id == 6


def test_load_wraps_storage_corrupted_error() -> None:
    backup = Path("expenses_corrupted_2026.json")
    storage_err = CorruptedStorageError("Broken JSON", backup_path=backup)
    storage = FakeStorage(load_error=storage_err)
    repo = ExpenseRepository(storage)

    with pytest.raises(RepositoryLoadError) as exc_info:
        repo.load()

    assert exc_info.value.backup_path == backup
    assert exc_info.value.__cause__ is storage_err
    assert storage.backup_called is False

    with pytest.raises(RepositoryNotInitializedError):
        repo.get_all()


def test_load_with_invalid_record_triggers_backup_and_fails_atomically() -> None:
    corrupted_record_data: StorageData = {
        "last_id": 2,
        "expenses": [
            {
                "id": 1,
                "amount": "100.00",
                "category": "їжа",
                "description": "Valid",
                "date": "2026-11-10",
            },
            {
                "id": 2,
                "amount": "-50.00",
                "category": "транспорт",
                "description": "Invalid",
                "date": "2026-11-11",
            },
        ],
    }
    storage = FakeStorage(initial_data=corrupted_record_data)
    repo = ExpenseRepository(storage)

    with pytest.raises(RepositoryLoadError) as exc_info:
        repo.load()

    assert storage.backup_called is True
    assert exc_info.value.backup_path == Path("fake_backup.json")

    with pytest.raises(RepositoryNotInitializedError):
        repo.get_all()


def test_get_by_id_returns_expense(sample_raw_data: StorageData) -> None:
    repo = ExpenseRepository(FakeStorage(sample_raw_data))
    repo.load()

    found = repo.get_by_id(1)

    assert found is not None
    assert found.expense_id == 1
    assert found.amount == Decimal("150.50")


def test_get_by_id_not_found_returns_none(sample_raw_data: StorageData) -> None:
    repo = ExpenseRepository(FakeStorage(sample_raw_data))
    repo.load()

    assert repo.get_by_id(999) is None


def test_get_all_returns_defensive_copy(sample_raw_data: StorageData) -> None:
    repo = ExpenseRepository(FakeStorage(sample_raw_data))
    repo.load()

    items = repo.get_all()
    items.clear()

    assert len(repo.get_all()) == 2


def test_add_overrides_preset_id_and_persists(sample_raw_data: StorageData) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    preset_expense = make_expense(expense_id=7, amount="250.00", description="Монітор")
    saved_expense = repo.add(preset_expense)

    assert saved_expense.expense_id == 3
    assert len(storage.save_calls) == 1
    assert storage.save_calls[-1]["last_id"] == 3


def test_add_wraps_storage_error_and_does_not_mutate_memory(
    sample_raw_data: StorageData,
) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    io_err = StorageError("Disk full")
    storage.save_error = io_err

    with pytest.raises(RepositorySaveError) as exc_info:
        repo.add(make_expense(amount="300.00"))

    assert exc_info.value.__cause__ is io_err
    assert len(repo.get_all()) == 2

    storage.save_error = None
    recovered = repo.add(make_expense(amount="300.00"))
    assert recovered.expense_id == 3


def test_update_replaces_frozen_instance_and_persists(
    sample_raw_data: StorageData,
) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    old_exp = repo.get_by_id(1)
    assert old_exp is not None

    modified_input = replace(old_exp, amount=Decimal("999.99"), description="Вечеря")
    updated_exp = repo.update(modified_input)

    assert updated_exp is not old_exp
    assert old_exp.amount == Decimal("150.50")
    assert repo.get_by_id(1) == updated_exp
    assert len(storage.save_calls) == 1


def test_update_wraps_storage_error_and_does_not_mutate_memory(
    sample_raw_data: StorageData,
) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    old_exp = repo.get_by_id(1)
    assert old_exp is not None

    io_err = StorageError("Permission denied")
    storage.save_error = io_err
    modified_input = replace(old_exp, amount=Decimal("999.99"))

    with pytest.raises(RepositorySaveError) as exc_info:
        repo.update(modified_input)

    assert exc_info.value.__cause__ is io_err
    current = repo.get_by_id(1)
    assert current is not None
    assert current.amount == Decimal("150.50")


def test_update_not_found_raises_error(sample_raw_data: StorageData) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    with pytest.raises(ExpenseNotFoundError):
        repo.update(make_expense(expense_id=999))

    assert len(storage.save_calls) == 0


def test_delete_last_expense_preserves_monotonic_last_id(
    sample_raw_data: StorageData,
) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    repo.delete(2)

    assert repo.get_by_id(2) is None
    assert len(repo.get_all()) == 1
    assert storage.save_calls[-1]["last_id"] == 2

    new_exp = repo.add(make_expense())
    assert new_exp.expense_id == 3


def test_delete_wraps_storage_error_and_does_not_mutate_memory(
    sample_raw_data: StorageData,
) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    io_err = StorageError("I/O error")
    storage.save_error = io_err

    with pytest.raises(RepositorySaveError) as exc_info:
        repo.delete(1)

    assert exc_info.value.__cause__ is io_err
    assert repo.get_by_id(1) is not None
    assert len(repo.get_all()) == 2


def test_delete_not_found_raises_error(sample_raw_data: StorageData) -> None:
    storage = FakeStorage(sample_raw_data)
    repo = ExpenseRepository(storage)
    repo.load()

    with pytest.raises(ExpenseNotFoundError):
        repo.delete(999)

    assert len(storage.save_calls) == 0


def test_integration_corrupted_json_file_creates_backup_and_raises_load_error(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "expenses.json"
    db_file.write_text("{ broken json ...", encoding="utf-8")

    storage = JSONStorage(db_file)
    repo = ExpenseRepository(storage)

    with pytest.raises(RepositoryLoadError) as exc_info:
        repo.load()

    backup_path = exc_info.value.backup_path
    assert backup_path is not None
    assert backup_path.exists()
    assert not db_file.exists()

    repo.load()
    assert repo.get_all() == []


def test_integration_invalid_record_in_valid_json_creates_backup_and_recovers(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "expenses.json"
    db_file.write_text(
        '{"last_id": 1, "expenses": [{"id": 1, "amount": "-10", "category": "їжа", "date": "2026-11-12"}]}',
        encoding="utf-8",
    )

    storage = JSONStorage(db_file)
    repo = ExpenseRepository(storage)

    with pytest.raises(RepositoryLoadError) as exc_info:
        repo.load()

    backup_path = exc_info.value.backup_path
    assert backup_path is not None
    assert backup_path.exists()
    assert not db_file.exists()

    repo.load()
    added = repo.add(make_expense(amount="75.00"))
    assert added.expense_id == 1
