"""Provide shared test fixtures that detach tests from repository data files.

Inputs: pytest fixture machinery along with module references for monkeypatching.
Outputs: Auto-used fixtures that supply temporary JSON datasets and patch configuration defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from subject_recommender import config, history_reset, io


@pytest.fixture(autouse=True)
def temporary_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Create and configure an isolated data directory for all tests.

    Inputs: `monkeypatch` for swapping module attributes and `tmp_path_factory` for generating a temporary folder.
    Outputs: None directly; patches configuration and IO modules to point at the temporary datasets.
    """

    data_dir = tmp_path_factory.mktemp("data")
    predictions_path = Path(data_dir, "predicted_grades.json")
    history_path = Path(data_dir, "history.json")

    predictions_path.write_text(json.dumps({"Maths": 0.5}), encoding="utf-8")
    history_path.write_text(
        json.dumps([{"subject": "Maths", "type": "Quiz", "score": 50, "date": "2025-01-01"}]),
        encoding="utf-8",
    )

    monkeypatch.setattr(io, "_DATA_DIR", data_dir)
    monkeypatch.setattr(config, "TEST_PREDICTED_GRADES_PATH", predictions_path.name)
    monkeypatch.setattr(config, "TEST_HISTORY_PATH", history_path.name)
    monkeypatch.setattr(history_reset, "_DATA_DIR", data_dir)
    monkeypatch.setattr(history_reset, "_DEFAULT_HISTORY_FILENAME", history_path.name)
