"""Combine weighted scores with predicted grades for subject recommendations.

Inputs: WeightedHistory dictionaries produced by `weighting.apply_weighting`.
Outputs: dict[str, float] containing floored blended scores per subject.
"""

from __future__ import annotations

from math import floor

from .. import io
from .weighting import WeightedHistory


def aggregate_scores(weighted_history: WeightedHistory) -> dict[str, float]:
    """Return floored per-subject scores blending defaults and results.

    Inputs: WeightedHistory mapping subject identifiers to weighted totals and weights.
    Outputs: dict[str, float] where each subject is mapped to a floored blended score.
    """
    predicted_grades = io.get_predicted_grades()
    performance_weights = io.get_performance_weights()

    default_weight = performance_weights["recent_weight"]
    result_weight = performance_weights["history_weight"]

    aggregated: dict[str, float] = {}

    for subject, predicted_grade in predicted_grades.items():
        weighted = weighted_history.get(subject, {"weighted": 0.0, "weight": 0.0})
        weighted_total = weighted["weighted"]
        weight_total = weighted["weight"]

        result_average = (weighted_total / weight_total) if weight_total else 0.0

        combined_score = (predicted_grade * default_weight) + (result_average * result_weight)

        aggregated[subject] = floor(combined_score * 100) / 100

    return aggregated
