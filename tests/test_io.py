"""Tests covering IO helper functions and their configuration bindings.

Inputs: pytest fixtures (`monkeypatch`, `tmp_path`) along with JSON samples.
Outputs: Dict responses reflecting configuration values or parsed data sets.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from subject_recommender import config, io


def test_get_assessment_weights_reflects_config() -> None:
    """Ensure assessment weight lookups mirror config constants.

    Inputs: None beyond imported configuration module.
    Outputs: Dict mapping strings to floats matching config attributes.
    """

    weights = io.get_assessment_weights()

    assert weights == {
        "Revision": config.REVISION_WEIGHT,
        "Homework": config.HOMEWORK_WEIGHT,
        "Quiz": config.QUIZ_WEIGHT,
        "Topic Test": config.TOPIC_TEST_WEIGHT,
        "Mock Exam": config.MOCK_EXAM_WEIGHT,
        "Exam": config.EXAM_WEIGHT,
    }


def test_get_performance_weights_reflects_config() -> None:
    """Verify performance weight response tracks config overrides.

    Inputs: None beyond imported configuration module.
    Outputs: Dict containing the two expected weighting factors.
    """

    weights = io.get_performance_weights()

    assert weights == {
        "recent_weight": config.RECENT_WEIGHT,
        "history_weight": config.HISTORY_WEIGHT,
    }


def test_get_session_defaults_reflects_config() -> None:
    """Confirm session defaults mirror session-related config values.

    Inputs: None beyond configuration state.
    Outputs: Dict describing count and durations.
    """

    defaults = io.get_session_defaults()

    assert defaults == {
        "count": config.SESSION_COUNT,
        "session_time": config.SESSION_TIME_MINUTES,
        "break_time": config.BREAK_TIME_MINUTES,
        "shots": config.SHOTS,
    }


def test_get_predicted_grades_reads_dataset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure data loading reads JSON content from the configured directory.

    Inputs: `monkeypatch` overriding `_DATA_DIR` and a temporary JSON file path.
    Outputs: Dict identical to the JSON payload contents.
    """

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    payload = [{"Maths": 0.5, "French": 0.4}]
    predictions_path = data_dir / "predicted_grades.json"
    predictions_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(io, "_DATA_DIR", data_dir)

    assert io.get_predicted_grades() == {"Maths": 0.5, "French": 0.4}


def test_get_predicted_grades_raises_for_empty_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate empty datasets raise `ValueError`.

    Inputs: Temporary JSON file containing an empty list, patched data directory.
    Outputs: Raised ValueError asserted via pytest.
    """

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "predicted_grades.json").write_text("[]", encoding="utf-8")

    monkeypatch.setattr(io, "_DATA_DIR", data_dir)

    with pytest.raises(ValueError):
        io.get_predicted_grades()


def test_get_predicted_grades_raises_for_invalid_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate invalid payload types raise `TypeError`.

    Inputs: Temporary JSON file containing a string, patched data directory.
    Outputs: Raised TypeError asserted via pytest.
    """

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "predicted_grades.json").write_text('"oops"', encoding="utf-8")

    monkeypatch.setattr(io, "_DATA_DIR", data_dir)

    with pytest.raises(TypeError):
        io.get_predicted_grades()


def test_get_study_history_reads_json_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure study history loading parses dictionaries and coalesces types.

    Inputs: Temporary JSON file containing two entries, patched `_DATA_DIR`.
    Outputs: list[dict[str, str | float]] mirroring the JSON content with coerced types.
    """

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    history_path = data_dir / "history.json"
    payload = [
        {"subject": "Maths", "type": "Quiz", "score": 65, "date": "2025-03-01"},
        {"subject": "French", "type": "Exam", "score": 72.5, "date": "2025-03-02"},
    ]
    history_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(io, "_DATA_DIR", data_dir)

    history = io.get_study_history()

    assert history[0]["subject"] == "Maths"
    assert history[0]["score"] == pytest.approx(65.0)
    assert history[1]["score"] == pytest.approx(72.5)


def test_get_study_history_rejects_non_list_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate invalid payload types raise TypeError for study history.

    Inputs: Temporary JSON file containing a dictionary, patched `_DATA_DIR`.
    Outputs: Raised TypeError asserted via pytest.
    """

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    history_path = data_dir / "history.json"
    history_path.write_text('{"subject": "Maths"}', encoding="utf-8")

    monkeypatch.setattr(io, "_DATA_DIR", data_dir)

    with pytest.raises(TypeError):
        io.get_study_history()


def test_get_study_history_rejects_non_dict_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate individual entries must be dictionaries."""

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    history_path = data_dir / "history.json"
    history_path.write_text('["Maths"]', encoding="utf-8")

    monkeypatch.setattr(io, "_DATA_DIR", data_dir)

    with pytest.raises(TypeError):
        io.get_study_history()
