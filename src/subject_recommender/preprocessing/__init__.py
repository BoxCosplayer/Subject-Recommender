"""Provide orchestration helpers for the preprocessing pipeline.

Inputs: Iterables of history entries (`Mapping[str, str | float]` dictionaries).
Outputs: Normalised per-subject scores and the recommended subject label.
"""

from __future__ import annotations

from collections.abc import Iterable

from . import aggregation, normalisation, weighting
from .weighting import HistoryEntry

__all__ = ["calculate_normalised_scores", "recommend_subject"]


def calculate_normalised_scores(history: Iterable[HistoryEntry]) -> dict[str, float]:
    """Return normalised per-subject scores for the supplied history.

    Inputs: Iterable of history entries, each exposing `subject`, `type`, and `score`.
    Outputs: dict[str, float] mapping each subject to a probability-like normalised score.
    """
    weighted = weighting.apply_weighting(history)
    aggregated = aggregation.aggregate_scores(weighted)
    return normalisation.normalise_scores(aggregated)


def recommend_subject(history: Iterable[HistoryEntry]) -> tuple[dict[str, float], str]:
    """Return both the normalised scores and the lowest-scoring subject.

    Inputs: Iterable of history entries forwarded to `calculate_normalised_scores`.
    Outputs: Tuple containing the normalised scores dictionary and the recommended subject label.
    """
    normalised_scores = calculate_normalised_scores(history)
    subject = normalisation.choose_lowest_subject(normalised_scores)
    return normalised_scores, subject
