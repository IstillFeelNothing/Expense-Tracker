from pathlib import Path

from app import ExpenseApp
from json_storage import JSONStorage
from repository import ExpenseRepository
from view import ConsoleView

DEFAULT_DATA_FILE = Path("expenses.json")


def main() -> None:
    storage = JSONStorage(DEFAULT_DATA_FILE)
    repo = ExpenseRepository(storage)
    view = ConsoleView()
    app = ExpenseApp(repo=repo, view=view)

    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        view.show_message("\nРоботу перервано. До зустрічі!")


if __name__ == "__main__":
    main()
