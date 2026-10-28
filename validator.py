import datetime
from decimal import Decimal, InvalidOperation

INCORRECT_DATE_FORMAT_ERROR = (
    "Некоректний формат або значення дати. Очікується YYYY-MM-DD або DD.MM.YYYY."
)

MAX_EXPENSE_AMOUNT = Decimal("1000000.00")
MAX_EXPENSE_AGE_YEARS = 100
DATE_FORMATS = (
    "%Y-%m-%d",
    "%d.%m.%Y",
)


class ValidationError(Exception):
    pass


def parse_and_validate_amount(amount_str: str) -> Decimal:
    if not isinstance(amount_str, str):
        raise TypeError("Потрібно передати рядок, що представляє число.")

    if not amount_str.strip():
        raise ValidationError("Сума витрати не може бути порожньою.")

    cleaned = amount_str.strip().replace(",", ".")

    if "e" in cleaned.lower():
        raise ValidationError("Експоненціальний запис не підтримується")

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError("Некоректний формат числа") from None

    if amount.is_nan():
        raise ValidationError("Не є числом NaN.")

    if amount.is_infinite():
        raise ValidationError("Сума витрати не може бути нескінченною.")

    if amount <= Decimal(0):
        raise ValidationError("Сума витрати має бути більшою за 0.")

    if amount > MAX_EXPENSE_AMOUNT:
        raise ValidationError(
            f"Сума витрати перевищує максимально допустиме значення {MAX_EXPENSE_AMOUNT}."
        )

    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValidationError(
            "Сума витрати не може мати більше двох знаків після коми."
        )
    return amount


def parse_and_validate_date(
    date_str: str, today: datetime.date | None = None
) -> datetime.date:
    if not isinstance(date_str, str):
        raise TypeError("Потрібно передати рядок, що представляє дату.")

    cleaned_str = date_str.strip()

    if today is None:
        today = datetime.date.today()

    if not cleaned_str:
        return today

    parsed_date = None

    for fmt in DATE_FORMATS:
        try:
            parsed_date = datetime.datetime.strptime(cleaned_str, fmt).date()
            break
        except ValueError:
            continue

    if parsed_date is None:
        raise ValidationError(INCORRECT_DATE_FORMAT_ERROR)

    if parsed_date > today:
        raise ValidationError("Дата не може бути в майбутньому.")

    try:
        min_date = datetime.date(today.year - MAX_EXPENSE_AGE_YEARS, today.month, today.day)
    except ValueError:
        min_date = datetime.date(today.year - MAX_EXPENSE_AGE_YEARS, today.month, 28)

    if parsed_date < min_date:
        raise ValidationError(f"Дата не може бути старішою за {MAX_EXPENSE_AGE_YEARS} років.")

    return parsed_date
