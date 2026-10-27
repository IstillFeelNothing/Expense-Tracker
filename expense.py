import datetime
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Expense:
    amount: Decimal
    category: str
    description: str
    date: datetime.date
    expense_id: int | None = None