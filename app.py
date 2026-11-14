from collections.abc import Callable
from dataclasses import replace
from datetime import date, timedelta

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
from repository import (
    ExpenseNotFoundError,
    ExpenseRepository,
    RepositoryLoadError,
    RepositorySaveError,
)
from validator import (
    ValidationError,
    parse_and_validate_amount,
    parse_and_validate_category,
    parse_and_validate_date,
)
from view import ConsoleView, format_amount, format_date


def _parse_positive_int(raw: str) -> int:
    cleaned = raw.strip()
    if not cleaned.isdigit() or int(cleaned) <= 0:
        raise ValidationError("ID має бути цілим додатним числом.")
    return int(cleaned)


def _parse_month(raw: str) -> int:
    cleaned = raw.strip()
    if not cleaned.isdigit() or not 1 <= int(cleaned) <= 12:
        raise ValidationError("Місяць має бути числом від 1 до 12.")
    return int(cleaned)


def _parse_year(raw: str) -> int:
    cleaned = raw.strip()
    if not cleaned.isdigit() or not 1900 <= int(cleaned) <= 2100:
        raise ValidationError("Рік має бути коректним чотиризначним числом.")
    return int(cleaned)


class ExpenseApp:
    def __init__(
        self,
        repo: ExpenseRepository,
        view: ConsoleView,
        today_fn: Callable[[], date] = date.today,
    ) -> None:
        self._repo = repo
        self._view = view
        self._today_fn = today_fn
        self._commands: dict[str, Callable[[], None]] = {
            "1": self._add_expense,
            "2": self._list_expenses,
            "3": self._edit_expense,
            "4": self._delete_expense,
            "5": self._stats_today,
            "6": self._stats_week,
            "7": self._stats_month,
            "8": self._stats_year,
        }

    def run(self) -> None:
        if not self._init_storage():
            return

        while True:
            self._view.show_menu()
            choice = self._view.prompt("Оберіть дію: ")

            if choice == "0":
                self._view.show_message("До зустрічі!")
                break

            action = self._commands.get(choice)
            if action is None:
                self._view.show_error("Невідома команда. Оберіть пункт із меню.")
                continue

            action()

    def _init_storage(self) -> bool:
        try:
            self._repo.load()
            return True
        except RepositoryLoadError as exc:
            self._view.show_error(str(exc))
            if exc.backup_path is None:
                return False

            self._view.show_message(
                f"Створено резервну копію пошкодженого файлу: {exc.backup_path}"
            )
            try:
                self._repo.load()
                return True
            except RepositoryLoadError as retry_exc:
                self._view.show_error(str(retry_exc))
                return False

    def _add_expense(self) -> None:
        today = self._today_fn()
        amount = self._view.ask("Сума (грн): ", parse_and_validate_amount)
        category = self._view.ask(
            "Категорія (Enter — без категорії): ",
            parse_and_validate_category,
        )
        expense_date = self._view.ask(
            f"Дата (ДД.ММ.РРРР або Enter для {format_date(today)}): ",
            lambda raw: parse_and_validate_date(raw, today=today),
        )
        description = self._view.prompt("Опис (необов'язково): ")

        draft = Expense(
            amount=amount,
            category=category,
            date=expense_date,
            description=description,
        )
        try:
            saved = self._repo.add(draft)
            self._view.show_message(f"Витрату #{saved.expense_id} успішно додано.")
        except RepositorySaveError as exc:
            self._view.show_error(str(exc))

    def _list_expenses(self) -> None:
        self._view.show_expenses(self._repo.get_all())

    def _edit_expense(self) -> None:
        expenses = self._repo.get_all()
        if not expenses:
            self._view.show_message("Немає витрат для редагування.")
            return

        self._view.show_expenses(expenses)
        expense_id = self._view.ask(
            "Введіть ID витрати для редагування: ", _parse_positive_int
        )
        existing = self._repo.get_by_id(expense_id)
        if existing is None:
            self._view.show_error(f"Витрату з ID={expense_id} не знайдено.")
            return

        today = self._today_fn()
        new_amount = self._view.ask_optional(
            f"Нова сума [{format_amount(existing.amount)}] (Enter — залишити): ",
            parse_and_validate_amount,
            existing.amount,
        )
        new_category = self._view.ask_optional(
            f"Нова категорія [{existing.category}] (Enter — залишити): ",
            parse_and_validate_category,
            existing.category,
        )
        new_date = self._view.ask_optional(
            f"Нова дата [{format_date(existing.date)}] (Enter — залишити): ",
            lambda raw: parse_and_validate_date(raw, today=today),
            existing.date,
        )
        raw_desc = self._view.prompt(
            f"Новий опис [{existing.description}] (Enter — залишити, '-' — очистити): "
        )
        if raw_desc == "-":
            new_description = ""
        elif raw_desc:
            new_description = raw_desc
        else:
            new_description = existing.description

        updated = replace(
            existing,
            amount=new_amount,
            category=new_category,
            date=new_date,
            description=new_description,
        )
        try:
            self._repo.update(updated)
            self._view.show_message(f"Витрату #{expense_id} оновлено.")
        except (ExpenseNotFoundError, RepositorySaveError) as exc:
            self._view.show_error(str(exc))

    def _delete_expense(self) -> None:
        expenses = self._repo.get_all()
        if not expenses:
            self._view.show_message("Немає витрат для видалення.")
            return

        self._view.show_expenses(expenses)
        expense_id = self._view.ask(
            "Введіть ID витрати для видалення: ", _parse_positive_int
        )

        try:
            self._repo.delete(expense_id)
            self._view.show_message(f"Витрату #{expense_id} видалено.")
        except (ExpenseNotFoundError, RepositorySaveError) as exc:
            self._view.show_error(str(exc))

    def _stats_today(self) -> None:
        today = self._today_fn()
        start, end = get_day_period(today)
        self._show_period_stats(f"Витрати за {format_date(today)}", start, end)

    def _stats_week(self) -> None:
        today = self._today_fn()
        week_start = today - timedelta(days=6)
        start, end = get_week_period(week_start)
        self._show_period_stats(
            f"Витрати за 7 днів ({format_date(start)} – {format_date(today)})",
            start,
            end,
        )

    def _stats_month(self) -> None:
        year = self._view.ask("Рік (напр. 2026): ", _parse_year)
        month = self._view.ask("Місяць (1–12): ", _parse_month)
        start, end = get_month_period(year, month)
        self._show_period_stats(f"Витрати за {month:02d}.{year}", start, end)

    def _stats_year(self) -> None:
        year = self._view.ask("Рік (напр. 2026): ", _parse_year)
        start, end = get_year_period(year)
        self._show_period_stats(f"Витрати за {year} рік", start, end)

    def _show_period_stats(self, title: str, start: date, end: date) -> None:
        filtered = filter_by_period(self._repo.get_all(), start, end)
        total = total_expenses(filtered)
        by_cat = group_by_category(filtered)
        self._view.show_summary(title, total, by_cat)
