"""Expose configuration values and persisted datasets to the application.

Inputs: constants from `config.py` and JSON payloads stored under the `data/` directory.
Outputs: Dictionaries that modules such as preprocessing and sessions can consume directly.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config

_ROOT_DIR = Path(__file__).resolve().parents[2]
_DATA_DIR = _ROOT_DIR / "data"


def get_assessment_weights() -> dict[str, float]:
    """Return the weighting per assessment type.

    Inputs: None (reads module-level constants).
    Outputs: dict[str, float] mapping assessment names to weights.
    """
    return {
        "Revision": config.REVISION_WEIGHT,
        "Homework": config.HOMEWORK_WEIGHT,
        "Quiz": config.QUIZ_WEIGHT,
        "Topic Test": config.TOPIC_TEST_WEIGHT,
        "Mock Exam": config.MOCK_EXAM_WEIGHT,
        "Exam": config.EXAM_WEIGHT,
    }


def get_performance_weights() -> dict[str, float]:
    """Return recent/history weighting factors for preprocessing.

    Inputs: None.
    Outputs: dict[str, float] containing `recent_weight` and `history_weight`.
    """
    return {
        "recent_weight": config.RECENT_WEIGHT,
        "history_weight": config.HISTORY_WEIGHT,
    }


def get_session_defaults() -> dict[str, int]:
    """Return session parameters for session generation defaults.

    Inputs: None.
    Outputs: dict[str, int] describing session counts and timings.
    """
    return {
        "count": config.SESSION_COUNT,
        "session_time": config.SESSION_TIME_MINUTES,
        "break_time": config.BREAK_TIME_MINUTES,
        "spins": config.SPINS,
    }


def get_predicted_grades() -> dict[str, float]:
    """Load the predicted grades dataset from data/predicted_grades.json.

    Inputs: None beyond filesystem access to the bundled JSON file.
    Outputs: dict[str, float] mapping subjects to predicted grade scores.
    """
    predictions_path = _DATA_DIR / "predicted_grades.json"
    with predictions_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        if not payload:
            raise ValueError("predicted_grades dataset cannot be empty")
        payload = payload[0]

    if not isinstance(payload, dict):
        raise TypeError("predicted_grades dataset must be a dict or a list of dicts")

    return {str(subject): float(score) for subject, score in payload.items()}


def get_study_history() -> list[dict[str, str | float]]:
    """Return the stored study history entries.

    Inputs: JSON payload stored in `data/history.json`.
    Outputs: list[dict[str, str | float]] with the canonical history schema
    (`subject`, `type`, `score`, `date` fields).
    """
    history_path = _DATA_DIR / "history.json"
    with history_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise TypeError("history dataset must be a list of dictionaries")

    normalised_history: list[dict[str, str | float]] = []

    for entry in payload:
        if not isinstance(entry, dict):
            raise TypeError("history entries must be dictionaries")

        normalised_history.append(
            {
                "subject": str(entry.get("subject", "")),
                "type": str(entry.get("type", "")),
                "score": float(entry.get("score", 0.0)),
                "date": str(entry.get("date", "")),
            }
        )

    return normalised_history
