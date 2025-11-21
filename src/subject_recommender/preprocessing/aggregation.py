"""Combine weighted scores with predicted grades for subject recommendations.

Inputs: WeightedHistory dictionaries produced by `weighting.apply_weighting`.
Outputs: dict[str, float] containing floored blended scores per subject.
"""

from __future__ import annotations

from math import floor

from .. import io
from .weighting import WeightedHistory


def calculate_weighted_averages(weighted_history: WeightedHistory) -> dict[str, float]:
    """Return average scores per subject derived from weighted totals.

    Inputs: weighted_history (WeightedHistory): mapping of subject names to their weighted scores
    and accumulated weights.
    Outputs: dict[str, float]: per-subject averages, defaulting to zero when no weight exists.
    """
    averages: dict[str, float] = {}

    for subject, totals in weighted_history.items():
        weighted_total = float(totals.get("weighted", 0.0))
        weight_total = float(totals.get("weight", 0.0))
        averages[subject] = (weighted_total / weight_total) if weight_total else 0.0

    return averages


def aggregate_scores(weighted_history: WeightedHistory) -> dict[str, float]:
    """Return floored per-subject scores blending defaults and results.

    Inputs: WeightedHistory mapping subject identifiers to weighted totals and weights.
    Outputs: dict[str, float] where each subject is mapped to a floored blended score.
    """
    predicted_grades = io.get_predicted_grades()
    performance_weights = io.get_performance_weights()

    default_weight = performance_weights["recent_weight"]
    result_weight = performance_weights["history_weight"]

    weighted_averages = calculate_weighted_averages(weighted_history)
    aggregated: dict[str, float] = {}

    for subject, predicted_grade in predicted_grades.items():
        result_average = weighted_averages.get(subject, 0.0)
        combined_score = (predicted_grade * default_weight) + (result_average * result_weight)

        aggregated[subject] = floor(combined_score * 100) / 100

    return aggregated
