from collections.abc import Callable, Iterable
from datetime import date
from decimal import Decimal
from typing import TypeVar

from expense import Expense
from validator import ValidationError

T = TypeVar("T")

CATEGORY_COL_WIDTH = 18
DESCRIPTION_COL_WIDTH = 30
AMOUNT_COL_WIDTH = 16


def format_amount(amount: Decimal) -> str:
    quantized = amount.quantize(Decimal("0.01"))
    formatted = f"{quantized:,.2f}".replace(",", "\u00a0").replace(".", ",")
    return f"{formatted}\u00a0грн"


def format_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


class ConsoleView:
    def __init__(
        self,
        input_fn: Callable[[str], str] | None = None,
        output_fn: Callable[[str], None] | None = None,
    ) -> None:
        self._input = input_fn if input_fn is not None else input
        self._output = output_fn if output_fn is not None else print

    def show_message(self, message: str) -> None:
        self._output(message)

    def show_error(self, message: str) -> None:
        self._output(f"[Помилка] {message}")

    def show_menu(self) -> None:
        self._output("\n=== Трекер витрат ===")
        self._output("1. Додати витрату")
        self._output("2. Переглянути всі витрати")
        self._output("3. Редагувати витрату")
        self._output("4. Видалити витрату")
        self._output("5. Статистика за сьогодні")
        self._output("6. Статистика за тиждень (останні 7 днів)")
        self._output("7. Статистика за місяць")
        self._output("8. Статистика за рік")
        self._output("0. Вихід")

    def prompt(self, text: str) -> str:
        return self._input(text).strip()

    def ask(self, prompt: str, parser: Callable[[str], T]) -> T:
        while True:
            raw = self._input(prompt)
            try:
                return parser(raw)
            except ValidationError as exc:
                self.show_error(str(exc))

    def ask_optional(
        self,
        prompt: str,
        parser: Callable[[str], T],
        default: T,
    ) -> T:
        while True:
            raw = self._input(prompt)
            if not raw.strip():
                return default
            try:
                return parser(raw)
            except ValidationError as exc:
                self.show_error(str(exc))

    def show_expenses(self, expenses: Iterable[Expense]) -> None:
        items = list(expenses)
        if not items:
            self._output("Список витрат порожній.")
            return

        header = (
            f"{'ID':>4} | "
            f"{'Дата':<10} | "
            f"{'Категорія':<{CATEGORY_COL_WIDTH}} | "
            f"{'Сума':>{AMOUNT_COL_WIDTH}} | "
            f"Опис"
        )
        separator = "-" * len(header)
        self._output(header)
        self._output(separator)

        for exp in items:
            exp_id = str(exp.expense_id) if exp.expense_id is not None else "-"
            cat_display = _truncate(exp.category.capitalize(), CATEGORY_COL_WIDTH)
            desc_display = _truncate(exp.description, DESCRIPTION_COL_WIDTH)
            amount_display = format_amount(exp.amount)

            row = (
                f"{exp_id:>4} | "
                f"{format_date(exp.date):<10} | "
                f"{cat_display:<{CATEGORY_COL_WIDTH}} | "
                f"{amount_display:>{AMOUNT_COL_WIDTH}} | "
                f"{desc_display}"
            )
            self._output(row)

    def show_summary(
        self,
        title: str,
        total: Decimal,
        by_category: dict[str, Decimal],
    ) -> None:
        self._output(f"\n--- {title} ---")
        if not by_category:
            self._output("Витрат за цей період немає.")
            return

        for category, amount in by_category.items():
            cat_display = _truncate(category.capitalize(), CATEGORY_COL_WIDTH)
            self._output(
                f"  {cat_display:<{CATEGORY_COL_WIDTH}} : {format_amount(amount):>{AMOUNT_COL_WIDTH}}"
            )

        self._output("-" * (CATEGORY_COL_WIDTH + AMOUNT_COL_WIDTH + 5))
        self._output(
            f"  {'Разом':<{CATEGORY_COL_WIDTH}} : {format_amount(total):>{AMOUNT_COL_WIDTH}}"
        )
