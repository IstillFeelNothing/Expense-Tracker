from collections.abc import Callable
from dataclasses import replace
from functools import wraps
from pathlib import Path
from typing import Concatenate, ParamSpec, TypeVar

from expense import Expense, InvalidExpenseDataError
from storage_protocol import (
    CorruptedStorageError,
    StorageData,
    StorageError,
    StorageProtocol,
)

P = ParamSpec("P")
R = TypeVar("R")


class RepositoryError(Exception):
    pass


class RepositoryLoadError(RepositoryError):
    def __init__(self, message: str, backup_path: Path | None = None) -> None:
        super().__init__(message)
        self.backup_path = backup_path


class RepositorySaveError(RepositoryError):
    pass


class ExpenseNotFoundError(RepositoryError):
    pass


class RepositoryNotInitializedError(RuntimeError):
    pass


def _require_initialized(
    method: Callable[Concatenate["ExpenseRepository", P], R],
) -> Callable[Concatenate["ExpenseRepository", P], R]:
    @wraps(method)
    def wrapper(self: "ExpenseRepository", /, *args: P.args, **kwargs: P.kwargs) -> R:
        if not self._is_loaded:
            raise RepositoryNotInitializedError(
                "Репозиторій не ініціалізовано. Викличте load() перед роботою з даними."
            )
        return method(self, *args, **kwargs)

    return wrapper


class ExpenseRepository:
    def __init__(self, storage: StorageProtocol) -> None:
        self._storage = storage
        self._expenses: dict[int, Expense] = {}
        self._last_id: int = 0
        self._is_loaded: bool = False

    def load(self) -> None:
        try:
            raw_data = self._storage.load()
        except CorruptedStorageError as err:
            raise RepositoryLoadError(
                f"Помилка читання сховища: {err}",
                backup_path=err.backup_path,
            ) from err
        except StorageError as err:
            raise RepositoryLoadError(
                f"Помилка доступу до сховища: {err}",
                backup_path=None,
            ) from err

        try:
            raw_last_id = raw_data.get("last_id", 0)
            if type(raw_last_id) is not int or raw_last_id < 0:
                raise ValueError(f"Некоректний last_id: {raw_last_id!r}")

            raw_expenses = raw_data.get("expenses", [])
            if not isinstance(raw_expenses, list):
                raise ValueError("Поле 'expenses' повинно бути списком")

            parsed_expenses: dict[int, Expense] = {}
            for item in raw_expenses:
                expense = Expense.from_dict(item)
                if expense.expense_id is None:
                    raise ValueError("Запис у сховищі не має обов'язкового поля 'id'")
                if expense.expense_id in parsed_expenses:
                    raise ValueError(f"Дублікат id={expense.expense_id} у сховищі")
                parsed_expenses[expense.expense_id] = expense

        except (InvalidExpenseDataError, KeyError, ValueError, TypeError) as err:
            try:
                backup_path = self._storage.backup_corrupted_data()
            except StorageError as backup_err:
                raise RepositoryLoadError(
                    f"Невалідний запис у сховищі ({err}) і не вдалося створити бекап ({backup_err}).",
                    backup_path=None,
                ) from err

            raise RepositoryLoadError(
                f"Невалідний запис у сховищі: {err}",
                backup_path=backup_path,
            ) from err

        self._expenses = parsed_expenses
        self._last_id = raw_last_id
        self._is_loaded = True

    @_require_initialized
    def get_all(self) -> list[Expense]:
        return list(self._expenses.values())

    @_require_initialized
    def get_by_id(self, expense_id: int) -> Expense | None:
        return self._expenses.get(expense_id)

    @_require_initialized
    def add(self, expense: Expense) -> Expense:
        new_id = self._last_id + 1
        created_expense = replace(expense, expense_id=new_id)

        next_expenses = {**self._expenses, new_id: created_expense}
        self._persist(next_expenses, new_id)

        self._expenses = next_expenses
        self._last_id = new_id
        return created_expense

    @_require_initialized
    def update(self, expense: Expense) -> Expense:
        if expense.expense_id is None or expense.expense_id not in self._expenses:
            raise ExpenseNotFoundError(
                f"Витрату з id={expense.expense_id} не знайдено для оновлення."
            )

        next_expenses = {**self._expenses, expense.expense_id: expense}
        self._persist(next_expenses, self._last_id)

        self._expenses = next_expenses
        return expense

    @_require_initialized
    def delete(self, expense_id: int) -> None:
        if expense_id not in self._expenses:
            raise ExpenseNotFoundError(
                f"Витрату з id={expense_id} не знайдено для видалення."
            )

        next_expenses = {k: v for k, v in self._expenses.items() if k != expense_id}
        self._persist(next_expenses, self._last_id)

        self._expenses = next_expenses

    def _persist(self, expenses: dict[int, Expense], last_id: int) -> None:
        payload: StorageData = {
            "last_id": last_id,
            "expenses": [exp.to_dict() for exp in expenses.values()],
        }
        try:
            self._storage.save(payload)
        except StorageError as err:
            raise RepositorySaveError(f"Не вдалося зберегти зміни: {err}") from err
