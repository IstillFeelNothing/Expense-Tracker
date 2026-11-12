from pathlib import Path
from typing import Any, Protocol, TypedDict


class StorageData(TypedDict):
    last_id: int
    expenses: list[dict[str, Any]]


def make_empty_storage_data() -> StorageData:
    return {
        "last_id": 0,
        "expenses": [],
    }


class StorageError(Exception):
    pass


class CorruptedStorageError(StorageError):
    def __init__(self, message: str, backup_path: Path) -> None:
        super().__init__(message)
        self.backup_path = backup_path


class StorageProtocol(Protocol):
    def load(self) -> StorageData: ...

    def save(self, data: StorageData) -> None: ...

    def backup_corrupted_data(self) -> Path: ...
