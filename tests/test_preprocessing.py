"""Tests for preprocessing helpers covering weighting, aggregation, and normalisation.

Inputs: pytest fixtures alongside dictionaries that mimic history entries,
predicted grades, and weighting factors.
Outputs: Assertions validating `Dict[str, Dict[str, float]]` and `Dict[str, float]`
results returned by the preprocessing modules.
"""

from __future__ import annotations

from datetime import date
from math import floor

import pytest

from subject_recommender import preprocessing
from subject_recommender.preprocessing import aggregation, normalisation, weighting


def test_apply_weighting_applies_configured_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate weighted history totals match configured weights.

    Inputs: `monkeypatch` fixture overriding `weighting.io.get_assessment_weights`
    and a list of history entries (`list[dict[str, str | float]]`).
    Outputs: `weighting.apply_weighting` response (`Dict[str, Dict[str, float]]`)
    whose per-subject weighted sums and weight totals reflect the configuration.
    """

    monkeypatch.setattr(
        weighting.io,
        "get_assessment_weights",
        lambda: {"Exam": 2.0, "Quiz": 1.5},
    )
    monkeypatch.setattr(
        weighting.io,
        "get_predicted_grades",
        lambda: {"Maths": 0.7, "Physics": 0.6},
    )

    history = [
        {"subject": "Maths", "score": 75, "type": "Exam"},
        {"subject": "Maths", "score": 65, "type": "Quiz"},
        {"subject": "Physics", "score": 80, "type": "Exam"},
        {"subject": "Physics", "score": 50, "type": "Unknown"},
    ]

    weighted_history = weighting.apply_weighting(history)

    maths_exam_weight = 2.0 * (100 - 75)
    maths_quiz_weight = 1.5 * (100 - 65)
    physics_exam_weight = 2.0 * (100 - 80)

    assert weighted_history["Maths"]["weighted"] == pytest.approx((75 * maths_exam_weight) + (65 * maths_quiz_weight))
    assert weighted_history["Maths"]["weight"] == pytest.approx(maths_exam_weight + maths_quiz_weight)
    assert weighted_history["Physics"]["weighted"] == pytest.approx(80 * physics_exam_weight)
    assert weighted_history["Physics"]["weight"] == pytest.approx(physics_exam_weight)


def test_apply_weighting_uses_predictions_for_non_positive_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure predicted grades determine weights when scores are non-positive.

    Inputs: `monkeypatch` fixture overriding IO helpers and a history list containing
    zero and negative scores.
    Outputs: WeightedHistory entry whose weights equal the floored prediction deltas,
    ensuring the fallback branch is exercised.
    """

    monkeypatch.setattr(weighting.io, "get_assessment_weights", lambda: {"Exam": 1.0})
    monkeypatch.setattr(
        weighting.io,
        "get_predicted_grades",
        lambda: {"History": 0.25},
    )

    history = [
        {"subject": "History", "score": 0, "type": "Exam"},
        {"subject": "History", "score": -10, "type": "Exam"},
        {"subject": "Art", "score": -5, "type": "Exam"},
    ]

    weighted_history = weighting.apply_weighting(history)

    expected_history_weight = floor(100 * (1.0 - 0.25))
    assert weighted_history["History"]["weight"] == pytest.approx(expected_history_weight * 2)
    assert weighted_history["History"]["weighted"] == pytest.approx(-10 * expected_history_weight)
    expected_art_weight = floor(100 * (1.0 - 0.1))
    assert weighted_history["Art"]["weight"] == pytest.approx(expected_art_weight)
    assert weighted_history["Art"]["weighted"] == pytest.approx(-5 * expected_art_weight)


def test_calculate_date_weight_covers_age_branches() -> None:
    """Ensure `_calculate_date_weight` clamps weights across date scenarios.

    Inputs: Weighting configuration dictionary and multiple date strings covering future, recent,
    threshold-exceeding, and invalid cases.
    Outputs: Floats reflecting maximum, scaled, minimum, and default weights respectively.
    """

    reference = date(2025, 6, 10)
    weighting_config = {"min_weight": 0.2, "max_weight": 1.0, "zero_day_threshold": 10}

    future_weight = weighting._calculate_date_weight("2025-06-15", weighting_config, reference)
    recent_weight = weighting._calculate_date_weight("2025-06-05", weighting_config, reference)
    old_weight = weighting._calculate_date_weight("2025-05-01", weighting_config, reference)
    invalid_weight = weighting._calculate_date_weight("not-a-date", weighting_config, reference)

    assert future_weight == pytest.approx(weighting_config["max_weight"])
    assert recent_weight < weighting_config["max_weight"]
    assert old_weight == pytest.approx(weighting_config["min_weight"])
    assert invalid_weight == pytest.approx(weighting_config["max_weight"])


def test_aggregate_scores_combines_defaults_and_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure aggregation favours weighted history averages with predicted fallbacks.

    Inputs: `monkeypatch` fixture replacing IO calls to provide `Dict[str, float]`
    predictions plus a `WeightedHistory`.
    Outputs: `Dict[str, float]` aggregated scores floored to two decimal places,
    using weighted averages when available and predictions otherwise.
    """

    monkeypatch.setattr(
        aggregation.io,
        "get_predicted_grades",
        lambda: {"Maths": 8.989, "History": 6.0},
    )

    weighted_history = {
        "Maths": {"weighted": 15.554, "weight": 2.0},
    }

    aggregated = aggregation.aggregate_scores(weighted_history)

    assert aggregated["Maths"] == pytest.approx(7.77)
    assert aggregated["History"] == pytest.approx(6.0)


def test_normalise_scores_uses_io_predictions_when_missing_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm normalisation pulls predictions from IO if not supplied.

    Inputs: `monkeypatch` fixture overriding `normalisation.io.get_predicted_grades`
    to return a `Dict[str, float]`.
    Outputs: Normalised `Dict[str, float]` whose probabilities sum to one.
    """

    monkeypatch.setattr(
        normalisation.io,
        "get_predicted_grades",
        lambda: {"Maths": 3.0, "French": 1.0},
    )

    normalised = normalisation.normalise_scores()

    assert normalised["Maths"] == pytest.approx(0.75)
    assert normalised["French"] == pytest.approx(0.25)
    assert sum(normalised.values()) == pytest.approx(1.0)


def test_normalise_scores_handles_zero_totals() -> None:
    """Check normalisation gracefully handles zero totals.

    Inputs: Explicit predictions dictionary with zero-valued floats.
    Outputs: Normalised `Dict[str, float]` maintaining zero entries without division errors.
    """

    normalised = normalisation.normalise_scores({"Biology": 0.0, "Chemistry": 0.0})

    assert normalised["Biology"] == pytest.approx(0.0)
    assert normalised["Chemistry"] == pytest.approx(0.0)
    assert sum(normalised.values()) == pytest.approx(0.0)


def test_choose_lowest_subject_returns_expected_choice() -> None:
    """Verify the chooser returns the subject with the smallest probability.

    Inputs: Normalised score mapping (`Dict[str, float]`).
    Outputs: String containing the subject label representing the lowest score.
    """

    normalised = {"Maths": 0.25, "Chemistry": 0.6, "History": 0.15}

    assert normalisation.choose_lowest_subject(normalised) == "History"


def test_choose_lowest_subject_raises_error_for_empty_input() -> None:
    """Ensure an empty mapping raises `ValueError`.

    Inputs: Empty dictionary representing the absence of normalised scores.
    Outputs: Raised `ValueError` per contract, asserted via pytest.
    """

    with pytest.raises(ValueError):
        normalisation.choose_lowest_subject({})


def test_calculate_normalised_scores_runs_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure the orchestration helper forwards outputs between each stage.

    Inputs: `monkeypatch` fixture replacing the weighting, aggregation, and normalisation calls.
    Outputs: Dict returned by `preprocessing.calculate_normalised_scores`.
    """

    history = [{"subject": "Maths", "type": "Quiz", "score": 75}]
    weighted_response = {"Maths": {"weighted": 150.0, "weight": 2.0}}
    aggregated_response = {"Maths": 12.5}

    monkeypatch.setattr(
        preprocessing.weighting,
        "apply_weighting",
        lambda entries: weighted_response if entries == history else {},
    )
    monkeypatch.setattr(
        preprocessing.aggregation,
        "aggregate_scores",
        lambda values: aggregated_response if values == weighted_response else {},
    )
    monkeypatch.setattr(
        preprocessing.normalisation,
        "normalise_scores",
        lambda scores: {"Maths": 1.0} if scores == aggregated_response else {},
    )

    normalised = preprocessing.calculate_normalised_scores(history)

    assert normalised == {"Maths": 1.0}


def test_recommend_subject_returns_lowest_from_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `recommend_subject` surfaces both the scores and the recommended subject.

    Inputs: `monkeypatch` fixture replacing `calculate_normalised_scores` and chooser helper.
    Outputs: Tuple containing the patched scores dictionary and chosen subject.
    """

    expected_scores = {"Maths": 0.4, "History": 0.2}

    monkeypatch.setattr(
        preprocessing,
        "calculate_normalised_scores",
        lambda history: expected_scores,
    )
    monkeypatch.setattr(
        preprocessing.normalisation,
        "choose_lowest_subject",
        lambda scores: min(scores, key=scores.get),
    )

    scores, subject = preprocessing.recommend_subject([{}])

    assert scores == expected_scores
    assert subject == "History"
