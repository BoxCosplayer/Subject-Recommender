"""Tests covering IO helper functions and their configuration bindings.

Inputs: pytest fixtures (`monkeypatch`, `tmp_path`) along with JSON samples.
Outputs: Dict responses reflecting configuration values or parsed data sets.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from subject_recommender import config, io


def _configure_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Return an isolated data directory with IO paths patched for the tests.

    Inputs: pytest `monkeypatch` fixture to override module globals and `tmp_path` providing a
    temporary root directory.
    Outputs: `Path` pointing to the created `data` directory that mimics the project layout.
    """

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(io, "_DATA_DIR", data_dir)
    return data_dir


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


def test_get_date_weighting_reflects_config() -> None:
    """Verify date weighting boundaries mirror configuration values.

    Inputs: None beyond imported configuration module.
    Outputs: Dict containing minimum, maximum, and threshold values.
    """

    weighting = io.get_date_weighting()

    assert weighting == {
        "min_weight": float(config.DATE_WEIGHT_MIN),
        "max_weight": float(config.DATE_WEIGHT_MAX),
        "zero_day_threshold": int(config.DATE_WEIGHT_ZERO_DAY_THRESHOLD),
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

    data_dir = _configure_data_dir(monkeypatch, tmp_path)
    payload = [{"Maths": 0.5, "French": 0.4}]
    predictions_path = data_dir / "predicted_grades.json"
    predictions_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(config, "TEST_PREDICTED_GRADES_PATH", predictions_path.name)

    assert io.get_predicted_grades() == {"Maths": 0.5, "French": 0.4}


def test_get_predicted_grades_raises_for_empty_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate empty datasets raise `ValueError`.

    Inputs: Temporary JSON file containing an empty list, patched data directory.
    Outputs: Raised ValueError asserted via pytest.
    """

    data_dir = _configure_data_dir(monkeypatch, tmp_path)
    predictions_path = data_dir / "predicted_grades.json"
    predictions_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(config, "TEST_PREDICTED_GRADES_PATH", predictions_path.name)

    with pytest.raises(ValueError):
        io.get_predicted_grades()


def test_get_predicted_grades_raises_for_invalid_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate invalid payload types raise `TypeError`.

    Inputs: Temporary JSON file containing a string, patched data directory.
    Outputs: Raised TypeError asserted via pytest.
    """

    data_dir = _configure_data_dir(monkeypatch, tmp_path)
    predictions_path = data_dir / "predicted_grades.json"
    predictions_path.write_text('"oops"', encoding="utf-8")

    monkeypatch.setattr(config, "TEST_PREDICTED_GRADES_PATH", predictions_path.name)

    with pytest.raises(TypeError):
        io.get_predicted_grades()


def test_get_predicted_grades_supports_absolute_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure `_resolve_data_path` honours absolute locations supplied via config.

    Inputs: Temporary JSON file with an absolute path patched into `config.TEST_PREDICTED_GRADES_PATH`.
    Outputs: Dict identical to the JSON payload, confirming absolute path resolution.
    """

    payload = {"History": 0.95}
    predictions_path = tmp_path / "absolute-predictions.json"
    predictions_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(config, "TEST_PREDICTED_GRADES_PATH", str(predictions_path))

    assert io.get_predicted_grades() == {"History": 0.95}


def test_get_study_history_reads_json_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure study history loading parses dictionaries and coalesces types.

    Inputs: Temporary JSON file containing two entries, patched `_DATA_DIR`.
    Outputs: list[dict[str, str | float]] mirroring the JSON content with coerced types.
    """

    data_dir = _configure_data_dir(monkeypatch, tmp_path)
    history_filename = config.TEST_HISTORY_PATH
    history_path = data_dir / history_filename
    payload = [
        {"subject": "Maths", "type": "Quiz", "score": 65, "date": "2025-03-01"},
        {"subject": "French", "type": "Exam", "score": 72.5, "date": "2025-03-02"},
    ]
    history_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(config, "TEST_HISTORY_PATH", history_path.name)

    history = io.get_study_history()

    assert history[0]["subject"] == "Maths"
    assert history[0]["score"] == pytest.approx(65.0)
    assert history[1]["score"] == pytest.approx(72.5)


def test_get_study_history_rejects_non_list_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate invalid payload types raise TypeError for study history.

    Inputs: Temporary JSON file containing a dictionary, patched `_DATA_DIR`.
    Outputs: Raised TypeError asserted via pytest.
    """

    data_dir = _configure_data_dir(monkeypatch, tmp_path)
    history_filename = config.TEST_HISTORY_PATH
    history_path = data_dir / history_filename
    history_path.write_text('{"subject": "Maths"}', encoding="utf-8")

    monkeypatch.setattr(config, "TEST_HISTORY_PATH", history_path.name)

    with pytest.raises(TypeError):
        io.get_study_history()


def test_get_study_history_rejects_non_dict_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate list entries must be dictionaries for study history loading.

    Inputs: Temporary JSON file containing a list of strings and `_DATA_DIR` override.
    Outputs: Raised TypeError asserted via pytest to confirm invalid entry handling.
    """

    data_dir = _configure_data_dir(monkeypatch, tmp_path)
    history_filename = config.TEST_HISTORY_PATH
    history_path = data_dir / history_filename
    history_path.write_text('["Maths"]', encoding="utf-8")

    monkeypatch.setattr(config, "TEST_HISTORY_PATH", history_path.name)

    with pytest.raises(TypeError):
        io.get_study_history()
