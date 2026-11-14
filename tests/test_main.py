from pathlib import Path

import pytest

from main import main


@pytest.mark.parametrize("interrupt_exc", [KeyboardInterrupt(), EOFError()])
def test_main_handles_ctrl_c_and_ctrl_d_gracefully(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    interrupt_exc: BaseException,
) -> None:
    monkeypatch.setattr("main.DEFAULT_DATA_FILE", tmp_path / "test_expenses.json")

    def raise_interrupt(_: str = "") -> str:
        raise interrupt_exc

    monkeypatch.setattr("builtins.input", raise_interrupt)

    main()

    captured = capsys.readouterr()
    assert "перервано" in captured.out.lower()
