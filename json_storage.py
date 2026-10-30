import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, TypedDict


class StorageData(TypedDict):
    last_id: int
    expenses: list[dict[str, Any]]


def make_empty_storage_data() -> StorageData:
    return {
        "last_id": 0,
        "expenses": [],
    }


class SchemaValidationError(Exception):
    pass


class CorruptedStorageError(Exception):
    def __init__(self, message: str, backup_path: Path) -> None:
        super().__init__(message)
        self.backup_path = backup_path


class JSONStorage:
    def __init__(self, file_path: Path | str) -> None:
        self.file_path = Path(file_path)

    def load(self) -> StorageData:
        if not self.file_path.exists():
            return make_empty_storage_data()

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            self._validate_schema(data)
            return data

        except (json.JSONDecodeError, UnicodeDecodeError, SchemaValidationError) as err:
            backup_path = self._create_backup()
            raise CorruptedStorageError(
                f"Файл сховища '{self.file_path.name}' пошкоджений ({err}). "
                f"Резервну копію збережено у '{backup_path.name}'.",
                backup_path=backup_path,
            ) from err

    def save(self, data: StorageData) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        temp_file = NamedTemporaryFile(
            mode="w",
            dir=self.file_path.parent,
            encoding="utf-8",
            delete=False,
            suffix=".tmp",
        )
        temp_path = Path(temp_file.name)

        try:
            with temp_file:
                json.dump(data, temp_file, ensure_ascii=False, indent=4)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            temp_path.replace(self.file_path)

        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _validate_schema(self, data: Any) -> None:
        if not isinstance(data, dict):
            raise SchemaValidationError("Кореневий елемент не є словником")

        last_id = data.get("last_id")
        if type(last_id) is not int or last_id < 0:
            raise SchemaValidationError(
                f"Ключ 'last_id' повинен бути невід'ємним цілим числом, отримано: {last_id!r}"
            )

        expenses = data.get("expenses")
        if not isinstance(expenses, list):
            raise SchemaValidationError("Ключ 'expenses' повинен бути списком")

        if not all(isinstance(item, dict) for item in expenses):
            raise SchemaValidationError(
                "Усі елементи списку 'expenses' повинні бути словниками"
            )

    def _create_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = (
            f"{self.file_path.stem}_corrupted_{timestamp}{self.file_path.suffix}"
        )
        backup_path = self.file_path.with_name(backup_name)

        self.file_path.rename(backup_path)
        return backup_path
