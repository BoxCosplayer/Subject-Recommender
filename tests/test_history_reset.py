"""Tests covering study history reset helpers.

Inputs: Temporary JSON datasets stored under an isolated `data` directory plus pytest fixtures.
Outputs: Assertions confirming path resolution, filtering behaviour, and CLI-style messaging.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from subject_recommender import history_reset


def test_resolve_history_path_supports_relative_and_absolute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure `_resolve_history_path` correctly handles both relative and absolute inputs.

    Inputs: Patched `_DATA_DIR` pointing to a temporary folder and a JSON file created within it.
    Outputs: Path instance matching the created file for both relative and absolute lookups.
    """

    history_file = tmp_path / "history.json"
    history_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(history_reset, "_DATA_DIR", tmp_path)

    relative_path = history_reset._resolve_history_path(history_file.name)
    absolute_path = history_reset._resolve_history_path(str(history_file))

    assert relative_path == history_file
    assert absolute_path == history_file


def test_resolve_history_path_raises_for_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate `_resolve_history_path` raises `FileNotFoundError` when the target file is absent.

    Inputs: Patched `_DATA_DIR` pointing to a temporary folder with no matching file.
    Outputs: Raised FileNotFoundError asserted via pytest.
    """

    monkeypatch.setattr(history_reset, "_DATA_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        history_reset._resolve_history_path("missing.json")


def test_filter_history_file_excludes_configured_types(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure `filter_history_file` removes revision-like entries and rewrites the dataset.

    Inputs: Temporary JSON payload containing both excluded and retained entry types.
    Outputs: Filtered list excluding "Revision" and "Not Studied" along with persisted JSON mirroring the filtered data.
    """

    monkeypatch.setattr(history_reset, "_DATA_DIR", tmp_path)
    history_file = tmp_path / "history.json"
    payload = [
        {"subject": "Maths", "type": "Revision", "score": 10},
        {"subject": "Chemistry", "type": "Not Studied", "score": -5},
        {"subject": "Physics", "type": "Quiz", "score": 75},
    ]
    history_file.write_text(json.dumps(payload), encoding="utf-8")

    filtered = history_reset.filter_history_file(history_file.name)

    assert filtered == [{"subject": "Physics", "type": "Quiz", "score": 75}]
    assert json.loads(history_file.read_text(encoding="utf-8")) == filtered


def test_main_reports_filtered_count(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Confirm `main` defaults to the configured filename and reports filtered entry totals.

    Inputs: Patched `_DATA_DIR` and `_DEFAULT_HISTORY_FILENAME` pointing to a temporary dataset
    containing excluded entries.

    Outputs: Printed message referencing the target filename and the number of records remaining after filtering.
    """

    monkeypatch.setattr(history_reset, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(history_reset, "_DEFAULT_HISTORY_FILENAME", "history.json")
    history_file = tmp_path / history_reset._DEFAULT_HISTORY_FILENAME
    history_file.write_text(json.dumps([{"type": "Not Studied"}, {"type": "Quiz"}]), encoding="utf-8")

    history_reset.main()

    message = capsys.readouterr().out.strip()
    assert "history.json" in message
    assert "1 records remain" in message
