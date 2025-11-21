"""Tests covering the session plan generator.

Inputs: Synthetic history dictionaries alongside monkeypatched preprocessing outputs.
Outputs: Assertions verifying plan subjects, appended entries, and history growth.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from subject_recommender.sessions import generate_session_plan
from subject_recommender.sessions import generator as generator_module


def test_generate_session_plan_returns_schedule_and_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure explicitly supplied history and parameters produce deterministic output.

    Inputs: `monkeypatch` fixture stubbing `_initialise_local_scores` with known values.
    Outputs: SessionPlan whose subjects and appended entries reflect the heuristic adjustments.
    """

    history = [
        {"subject": "Maths", "type": "Quiz", "score": 55, "date": "2025-03-01"},
        {"subject": "Chemistry", "type": "Exam", "score": 78, "date": "2025-03-02"},
    ]
    session_parameters = {"count": 2, "session_time": 45, "break_time": 15}

    monkeypatch.setattr(
        generator_module.io,
        "get_session_defaults",
        lambda: {"count": 2, "session_time": 45, "break_time": 15, "shots": 1},
    )
    monkeypatch.setattr(generator_module.io, "get_predicted_grades", lambda: {})
    monkeypatch.setattr(
        generator_module,
        "_initialise_local_scores",
        lambda _: {"Physics": 0.1, "History": 0.2},
    )
    monkeypatch.setattr(generator_module, "_persist_history", lambda entries: None)

    plans = generate_session_plan(
        history=history,
        session_parameters=session_parameters,
        session_date="2025-03-10",
    )

    assert len(plans) == 1
    plan = plans[0]
    assert plan.subjects == ["Physics", "History"]
    assert len(plan.history) == len(history) + 4
    revision_entries = [entry for entry in plan.new_entries if entry["type"] == "Revision"]
    penalty_entries = [entry for entry in plan.new_entries if entry["type"] == "Not Studied"]
    assert len(revision_entries) == 2
    assert len(penalty_entries) == 2
    assert any(entry["subject"] == "Maths" for entry in penalty_entries)


def test_generate_session_plan_loads_history_and_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the generator falls back to IO helpers when arguments are omitted.

    Inputs: Monkeypatched IO helpers returning deterministic history and defaults.
    Outputs: SessionPlan created without explicit history/parameter arguments.
    """

    stored_history = [
        {"subject": "Biology", "type": "Quiz", "score": 60, "date": "2025-02-01"},
    ]
    monkeypatch.setattr(generator_module.io, "get_study_history", lambda: stored_history)
    monkeypatch.setattr(
        generator_module.io,
        "get_session_defaults",
        lambda: {"count": 1, "session_time": 30, "break_time": 5, "shots": 1},
    )
    monkeypatch.setattr(
        generator_module.io,
        "get_predicted_grades",
        lambda: {"English Literature": 0.5},
    )
    monkeypatch.setattr(
        generator_module,
        "_initialise_local_scores",
        lambda _: {"English Literature": 0.05, "Maths": 0.2},
    )
    monkeypatch.setattr(generator_module, "_persist_history", lambda entries: None)

    plans = generate_session_plan(session_date="2025-04-01")

    assert len(plans) == 1
    plan = plans[0]
    assert plan.subjects == ["English Literature"]
    assert len(plan.history) == len(stored_history) + 2
    assert any(entry["type"] == "Not Studied" for entry in plan.new_entries)


def test_generate_session_plan_merges_partial_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure missing override keys fall back to configuration defaults."""

    history = [
        {"subject": "Geography", "type": "Quiz", "score": 70, "date": "2025-01-15"},
    ]
    monkeypatch.setattr(
        generator_module,
        "_initialise_local_scores",
        lambda _: {"Chemistry": 0.05, "Geography": 0.5},
    )
    monkeypatch.setattr(
        generator_module.io,
        "get_session_defaults",
        lambda: {"count": 3, "session_time": 40, "break_time": 10, "shots": 1},
    )
    monkeypatch.setattr(generator_module.io, "get_predicted_grades", lambda: {"Chemistry": 0.6})
    monkeypatch.setattr(generator_module, "_persist_history", lambda entries: None)

    plans = generate_session_plan(
        history=history,
        session_parameters={"count": 1, "session_time": 60},
        session_date="2025-05-01",
    )

    assert len(plans) == 1
    plan = plans[0]
    assert plan.subjects == ["Chemistry"]
    assert any(entry["type"] == "Not Studied" for entry in plan.new_entries)


def test_generate_session_plan_runs_multiple_shots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure the generator produces multiple plans when shots > 1."""

    history = [
        {"subject": "Maths", "type": "Quiz", "score": 55, "date": "2025-03-01"},
    ]
    monkeypatch.setattr(
        generator_module.io,
        "get_session_defaults",
        lambda: {"count": 1, "session_time": 45, "break_time": 15, "shots": 2},
    )
    monkeypatch.setattr(generator_module.io, "get_predicted_grades", lambda: {})

    shot_scores = iter(
        [
            {"Physics": 0.1, "History": 0.2},
            {"Physics": 0.6, "History": 0.4},
        ]
    )
    monkeypatch.setattr(
        generator_module,
        "_initialise_local_scores",
        lambda _: next(shot_scores),
    )

    persist_calls: list[list[dict[str, str | float]]] = []
    monkeypatch.setattr(
        generator_module,
        "_persist_history",
        lambda entries: persist_calls.append(list(entries)),
    )

    plans = generate_session_plan(history=history, session_date="2025-03-10")

    assert len(plans) == 2
    assert plans[0].subjects == ["Physics"]
    assert plans[1].subjects == ["History"]
    assert len(persist_calls) == 2


def test_generate_session_plan_leaves_predictions_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure generating multiple shots never mutates the predicted grades dataset on disk.

    Inputs: Temporary prediction and history files alongside monkeypatched session defaults and score initialiser.
    Outputs: Assertions confirming the predictions JSON content remains identical after plan generation.
    """

    predictions_path = tmp_path / "predicted_grades.json"
    predictions_payload = {"Maths": 0.5, "History": 0.35}
    predictions_path.write_text(json.dumps(predictions_payload), encoding="utf-8")
    monkeypatch.setattr(generator_module.io, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(generator_module.config, "TEST_PREDICTED_GRADES_PATH", predictions_path.name)

    history_path = tmp_path / "gcse_test-grades.json"
    history_payload = [{"subject": "Maths", "type": "Quiz", "score": 55, "date": "2025-03-01"}]
    history_path.write_text(json.dumps(history_payload), encoding="utf-8")
    monkeypatch.setattr(generator_module.config, "TEST_HISTORY_PATH", history_path.name)

    monkeypatch.setattr(
        generator_module.io,
        "get_session_defaults",
        lambda: {"count": 1, "session_time": 30, "break_time": 5, "shots": 2},
    )
    monkeypatch.setattr(
        generator_module,
        "_initialise_local_scores",
        lambda _: {"Maths": 0.1, "History": 0.2},
    )

    original_serialised = predictions_path.read_text(encoding="utf-8")

    plans = generate_session_plan(session_date="2025-08-01")

    assert len(plans) == 2
    assert json.loads(predictions_path.read_text(encoding="utf-8")) == predictions_payload
    assert predictions_path.read_text(encoding="utf-8") == original_serialised


def test_initialise_local_scores_scales_aggregated_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure `_initialise_local_scores` divides aggregated scores by 100."""

    history = [
        {"subject": "Maths", "type": "Quiz", "score": 50, "date": "2025-01-01"},
    ]
    monkeypatch.setattr(
        generator_module.preprocessing.weighting,
        "apply_weighting",
        lambda entries: {"Maths": {"weighted": 50.0, "weight": 1.0}},
    )
    monkeypatch.setattr(
        generator_module.preprocessing.aggregation,
        "aggregate_scores",
        lambda weighted: {"Maths": 25.0},
    )

    assert generator_module._initialise_local_scores(history) == {"Maths": 0.25}


def test_calculate_predicted_grades_from_history_scales_weighted_averages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure regenerated predictions divide weighted averages by 100 and clamp negatives.

    Inputs: minimal history list with positive and negative scores plus custom assessment weights.
    Outputs: Dict mapping subjects to scaled predicted grades, clamping values below zero while
    applying weighting factors.
    """

    history = [
        {"subject": "Maths", "type": "Quiz", "score": 50, "date": "2025-03-01"},
        {"subject": "Maths", "type": "Homework", "score": 70, "date": "2025-03-02"},
        {"subject": "French", "type": "Homework", "score": -10, "date": "2025-03-03"},
    ]

    monkeypatch.setattr(
        generator_module.io,
        "get_assessment_weights",
        lambda: {"Quiz": 2.0, "Homework": 1.0},
    )

    predictions = generator_module._calculate_predicted_grades_from_history(history)

    assert predictions["Maths"] == pytest.approx(0.5666666, rel=1e-3)
    assert predictions["French"] == pytest.approx(0.0)


def test_calculate_predicted_grades_skips_empty_subjects_and_zero_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure `_calculate_predicted_grades_from_history` handles empty subjects and non-positive weights.

    Inputs: History list containing an empty subject entry and a zero-weight assessment type,
    alongside monkeypatched assessment weights that force the weight <= 0 branch.
    Outputs: Predictions excluding the empty subject while returning a zero grade for the zero-weight entry.
    """

    history = [
        {"subject": "", "type": "Quiz", "score": 50},
        {"subject": "Geography", "type": "Zero Weight", "score": 60},
    ]

    monkeypatch.setattr(
        generator_module.io,
        "get_assessment_weights",
        lambda: {"Zero Weight": 0.0, "Quiz": 1.0},
    )

    predictions = generator_module._calculate_predicted_grades_from_history(history)

    assert "Geography" in predictions
    assert predictions["Geography"] == pytest.approx(0.0)
    assert "" not in predictions


def test_adjust_local_scores_updates_subject_weights() -> None:
    """Validate `_adjust_local_scores` mirrors AlgoTesting heuristics.

    Inputs: Inline dictionary representing the local scores map along with explicit
    integers for the session duration and break length.
    Outputs: Mutated dictionary confirming the studied subject increases and other
    subjects receive a fixed penalty of 0.005.
    """

    scores = {"Maths": 0.2, "Chemistry": 0.5}

    generator_module._adjust_local_scores(scores, "Maths", session_time=40, break_time=10)

    assert scores["Maths"] > 0.2
    assert scores["Chemistry"] == pytest.approx(0.495)


def test_adjust_local_scores_scales_with_effective_minutes() -> None:
    """Ensure `_adjust_local_scores` reacts to the effective study duration.

    Inputs: Two local score dictionaries updated via `_adjust_local_scores`
    with short and long study durations.
    Outputs: Derived deltas confirming the studied subject reacts to session time
    while non-studied subjects apply a constant penalty.
    """

    short_scores = {"Maths": 0.3, "Chemistry": 0.4}
    long_scores = {"Maths": 0.3, "Chemistry": 0.4}

    generator_module._adjust_local_scores(
        short_scores,
        "Maths",
        session_time=10,
        break_time=9,
    )
    generator_module._adjust_local_scores(
        long_scores,
        "Maths",
        session_time=180,
        break_time=5,
    )

    short_studied_increase = short_scores["Maths"] - 0.3
    long_studied_increase = long_scores["Maths"] - 0.3
    short_not_studied_drop = 0.4 - short_scores["Chemistry"]
    long_not_studied_drop = 0.4 - long_scores["Chemistry"]

    assert short_studied_increase < long_studied_increase
    assert short_not_studied_drop == pytest.approx(long_not_studied_drop)
    assert short_not_studied_drop == pytest.approx(0.005)


def test_resolve_session_parameters_adds_default_shot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure `_resolve_session_parameters` always returns a `shots` key."""

    monkeypatch.setattr(
        generator_module.io,
        "get_session_defaults",
        lambda: {"count": 1, "session_time": 30, "break_time": 5},
    )

    resolved = generator_module._resolve_session_parameters(None)

    assert resolved["shots"] == 1


def test_persist_history_writes_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure `_persist_history` creates the history file when missing."""

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(generator_module.config, "TEST_HISTORY_PATH", "predicted_grades.json")
    monkeypatch.setattr(generator_module.io, "_DATA_DIR", data_dir)

    entries = [
        {"subject": "Maths", "type": "Revision", "score": 75.0, "date": "2025-03-10"},
    ]

    generator_module._persist_history(entries)

    history_path = data_dir / generator_module.config.TEST_HISTORY_PATH
    payload = json.loads(history_path.read_text(encoding="utf-8"))

    assert payload[-1]["subject"] == "Maths"


def test_persist_history_appends_to_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure `_persist_history` appends to existing datasets."""

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(generator_module.config, "TEST_PREDICTED_GRADES_PATH", "predicted_grades.json")
    history_path = data_dir / generator_module.config.TEST_HISTORY_PATH
    history_path.write_text(
        json.dumps([{"subject": "History", "type": "Revision", "score": 60, "date": "2025-03-09"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(generator_module.io, "_DATA_DIR", data_dir)

    entries = [
        {"subject": "Chemistry", "type": "Revision", "score": 90.0, "date": "2025-03-10"},
    ]

    generator_module._persist_history(entries)

    payload = json.loads(history_path.read_text(encoding="utf-8"))

    assert len(payload) == 2
    assert payload[-1]["subject"] == "Chemistry"


def test_persist_history_ignores_empty_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure `_persist_history` no-ops when given an empty payload."""

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(generator_module.config, "TEST_PREDICTED_GRADES_PATH", "predicted_grades.json")
    monkeypatch.setattr(generator_module.io, "_DATA_DIR", data_dir)

    generator_module._persist_history([])

    assert not (data_dir / generator_module.config.TEST_HISTORY_PATH).exists()
