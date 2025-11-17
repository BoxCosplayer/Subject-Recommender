"""Normalize aggregated scores and choose the next subject."""

from __future__ import annotations

from .. import io


def normalise_scores(
    predicted_grades: dict[str, float] | None = None,
) -> dict[str, float]:
    """Return scores normalized to sum to one."""
    if predicted_grades is None:
        predicted_grades = io.get_predicted_grades()

    total = sum(predicted_grades.values()) or 1.0
    return {subject: score / total for subject, score in predicted_grades.items()}


def choose_lowest_subject(normalised_scores: dict[str, float]) -> str:
    """Return the subject with the lowest normalized score."""
    if not normalised_scores:
        raise ValueError("normalised_scores cannot be empty")
    return min(normalised_scores, key=lambda subject: normalised_scores[subject])
