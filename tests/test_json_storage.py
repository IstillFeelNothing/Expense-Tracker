import json
from pathlib import Path
from typing import Any

import pytest

from json_storage import CorruptedStorageError, JSONStorage, make_empty_storage_data


@pytest.fixture
def storage_path(tmp_path: Path) -> Path:
    return tmp_path / "expenses.json"


@pytest.fixture
def storage(storage_path: Path) -> JSONStorage:
    return JSONStorage(storage_path)


def test_make_empty_storage_data_returns_fresh_instances() -> None:
    data_1 = make_empty_storage_data()
    data_2 = make_empty_storage_data()

    data_1["expenses"].append({"id": 1, "amount": "10.00"})

    assert data_1["expenses"] == [{"id": 1, "amount": "10.00"}]
    assert data_2["expenses"] == []
    assert data_1 is not data_2


def test_load_returns_empty_data_when_file_does_not_exist(
    storage: JSONStorage, storage_path: Path
) -> None:
    assert not storage_path.exists()

    data = storage.load()

    assert data == {"last_id": 0, "expenses": []}


def test_save_and_load_valid_data(storage: JSONStorage, storage_path: Path) -> None:
    payload = {
        "last_id": 2,
        "expenses": [
            {
                "id": 1,
                "amount": "150.50",
                "category": "Food",
                "date": "2026-10-30",
                "description": "Lunch at cafe",
            },
            {
                "id": 2,
                "amount": "20.00",
                "category": "Transport",
                "date": "2026-10-30",
                "description": "",
            },
        ],
    }

    storage.save(payload)

    assert storage_path.exists()
    loaded_data = storage.load()
    assert loaded_data == payload


def test_save_creates_atomic_file_and_leaves_no_tmp_files(
    storage: JSONStorage, storage_path: Path
) -> None:
    """Запис створює новий файл і гарантує відсутність залишкових .tmp файлів."""
    payload = make_empty_storage_data()

    storage.save(payload)
    assert storage_path.exists()
    tmp_files = list(storage_path.parent.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_save_preserves_utf8_encoding_without_ascii_escapes(
    storage: JSONStorage, storage_path: Path
) -> None:
    payload = {
        "last_id": 1,
        "expenses": [
            {
                "id": 1,
                "amount": "100.00",
                "category": "Харчування",
                "date": "2026-10-30",
                "description": "Кава та круасан",
            }
        ],
    }

    storage.save(payload)

    raw_text = storage_path.read_text(encoding="utf-8")
    assert "Харчування" in raw_text
    assert "Кава та круасан" in raw_text
    assert "\\u04" not in raw_text


def test_load_raises_corrupted_error_and_preserves_data_in_backup(
    storage: JSONStorage, storage_path: Path
) -> None:
    raw_corrupted_content = "{ invalid json structure content "
    storage_path.write_text(raw_corrupted_content, encoding="utf-8")

    with pytest.raises(CorruptedStorageError) as exc_info:
        storage.load()

    error = exc_info.value
    assert "expenses_corrupted_" in error.backup_path.name
    assert error.backup_path.exists()
    assert not storage_path.exists()

    backup_content = error.backup_path.read_text(encoding="utf-8")
    assert backup_content == raw_corrupted_content


@pytest.mark.parametrize(
    "invalid_payload",
    [
        "not a dict string",
        {"expenses": []},
        {"last_id": True, "expenses": []},
        {"last_id": -5, "expenses": []},
        {"last_id": "abc", "expenses": []},
        {"last_id": 1, "expenses": "not a list"},
        {"last_id": 1, "expenses": [1, "abc", None]},
    ],
)
def test_load_raises_corrupted_error_on_invalid_schema(
    storage: JSONStorage, storage_path: Path, invalid_payload: Any
) -> None:
    storage_path.write_text(json.dumps(invalid_payload), encoding="utf-8")

    with pytest.raises(CorruptedStorageError) as exc_info:
        storage.load()

    assert not storage_path.exists()
    assert exc_info.value.backup_path.exists()
    assert "пошкоджений" in str(exc_info.value)
