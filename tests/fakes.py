from copy import deepcopy
from pathlib import Path

from storage_protocol import (
    CorruptedStorageError,
    StorageData,
    StorageError,
    make_empty_storage_data,
)


class FakeStorage:
    def __init__(
        self,
        initial_data: StorageData | None = None,
        load_error: Exception | None = None,
        save_error: StorageError | None = None,
        corrupted_once_backup: Path | None = None,
    ) -> None:
        self.data: StorageData = (
            deepcopy(initial_data)
            if initial_data is not None
            else make_empty_storage_data()
        )
        self.load_error = load_error
        self.save_error = save_error
        self.corrupted_once_backup = corrupted_once_backup
        self.save_calls: list[StorageData] = []
        self.backup_called: bool = False

    def load(self) -> StorageData:
        if self.load_error is not None:
            raise self.load_error

        if self.corrupted_once_backup is not None:
            backup = self.corrupted_once_backup
            self.corrupted_once_backup = None
            self.data = make_empty_storage_data()
            raise CorruptedStorageError(
                f"Файл пошкоджено. Резервну копію збережено у '{backup.name}'.",
                backup_path=backup,
            )

        return deepcopy(self.data)

    def save(self, data: StorageData) -> None:
        if self.save_error is not None:
            raise self.save_error
        saved_copy = deepcopy(data)
        self.data = saved_copy
        self.save_calls.append(saved_copy)

    def backup_corrupted_data(self) -> Path:
        self.backup_called = True
        return Path("fake_backup.json")
