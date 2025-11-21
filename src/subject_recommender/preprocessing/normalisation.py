"""Normalise aggregated scores and choose the next subject for revision.

Inputs: Aggregated per-subject scores supplied directly or loaded via IO helpers.
Outputs: Normalised score mapping that sums to one plus helpers to select candidates.
"""

from __future__ import annotations

from .. import io


def normalise_scores(
    predicted_grades: dict[str, float] | None = None,
) -> dict[str, float]:
    """Return scores normalised to sum to one.

    Inputs: predicted_grades (dict[str, float] | None): optional mapping of subjects to scores.
    Outputs: dict[str, float]: subject scores scaled so values sum to one (or zero when empty).
    """
    if predicted_grades is None:
        predicted_grades = io.get_predicted_grades()

    total = sum(predicted_grades.values()) or 1.0
    return {subject: score / total for subject, score in predicted_grades.items()}


def choose_lowest_subject(normalised_scores: dict[str, float]) -> str:
    """Return the subject with the lowest normalised score.

    Inputs: normalised_scores (dict[str, float]): mapping of subjects to probability-like scores.
    Outputs: str: subject label representing the lowest value; raises ValueError when empty.
    """
    if not normalised_scores:
        raise ValueError("normalised_scores cannot be empty")
    return min(normalised_scores, key=lambda subject: normalised_scores[subject])
