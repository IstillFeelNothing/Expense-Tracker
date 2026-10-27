from decimal import Decimal, InvalidOperation

MAX_EXPENSE_AMOUNT = Decimal("1000000.00")


class ValidationError(Exception):

    pass


def parse_and_validate_amount(amount_str: str) -> Decimal:
    if not isinstance(amount_str, str):
        raise TypeError("Потрібно передати рядок, що представляє число.")

    if not amount_str.strip():
        raise ValidationError("Сума витрати не може бути порожньою.")

    cleaned = amount_str.strip().replace(",",".")

    if "e" in cleaned.lower():
        raise ValidationError("Експоненціальний запис не підтримується")

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError("Некоректний формат числа") from None

    if amount.is_nan():
        raise ValidationError("Не є числом NaN.")

    if amount.is_infinite():
        raise ValidationError("Сума витрати не може бути нескінченной.")

    if amount <= Decimal(0):
        raise ValidationError("Сума витрати має бути більшою за 0.")

    if amount > MAX_EXPENSE_AMOUNT:
        raise ValidationError(f"Сума витрати перевищує максимально допустиме значення {MAX_EXPENSE_AMOUNT}.")

    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValidationError("Сума витрати не може мати більше двох знаків після коми.")
    return amount