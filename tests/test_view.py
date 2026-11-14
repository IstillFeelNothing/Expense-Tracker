from datetime import date
from decimal import Decimal

from expense import Expense
from validator import parse_and_validate_amount
from view import ConsoleView, format_amount


def test_format_amount_ukrainian_locale_with_nbsp() -> None:
    assert format_amount(Decimal("1250.5")) == "1\u00a0250,50\u00a0грн"
    assert format_amount(Decimal("0")) == "0,00\u00a0грн"
    assert format_amount(Decimal("1000000.99")) == "1\u00a0000\u00a0000,99\u00a0грн"


def test_view_ask_retries_until_valid_input() -> None:
    inputs = iter(["абв", "-10", "50.25"])
    outputs: list[str] = []
    view = ConsoleView(
        input_fn=lambda _: next(inputs),
        output_fn=outputs.append,
    )

    result = view.ask("Сума: ", parse_and_validate_amount)

    assert result == Decimal("50.25")
    assert len(outputs) == 2


def test_view_ask_optional_keeps_current_on_empty_input() -> None:
    inputs = iter(["   "])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    current = Decimal("300.00")
    result = view.ask_optional("Нова сума: ", parse_and_validate_amount, current)

    assert result == current
    assert outputs == []


def test_view_ask_optional_retries_on_invalid_then_parses() -> None:
    inputs = iter(["не_число", "450.75"])
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: next(inputs), output_fn=outputs.append)

    result = view.ask_optional(
        "Нова сума: ", parse_and_validate_amount, Decimal("300.00")
    )

    assert result == Decimal("450.75")
    assert len(outputs) == 1


def test_view_show_expenses_truncates_long_category_and_formats_date() -> None:
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: "", output_fn=outputs.append)

    long_category = "дуже_довга_назва_категорії_яка_не_поміщається_в_колонку"
    expenses = [
        Expense(
            expense_id=1,
            amount=Decimal("1250.5"),
            category=long_category,
            date=date(2026, 11, 14),
        )
    ]

    view.show_expenses(expenses)
    rendered = "\n".join(outputs)

    assert "14.11.2026" in rendered
    assert "1\u00a0250,50\u00a0грн" in rendered
    assert "…" in rendered
    assert long_category not in rendered


def test_view_show_expenses_empty_list() -> None:
    outputs: list[str] = []
    view = ConsoleView(input_fn=lambda _: "", output_fn=outputs.append)

    view.show_expenses([])

    assert any("порожній" in line.lower() for line in outputs)
