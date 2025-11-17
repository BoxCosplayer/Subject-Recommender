"""Apply assessment weights to historical grade entries."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping

from .. import io

HistoryEntry = Mapping[str, float | str]
WeightedHistory = dict[str, dict[str, float]]  # {"subject": {"weighted": float, "weight": float}}


def apply_weighting(history: Iterable[HistoryEntry]) -> WeightedHistory:
    """Return running totals of weighted scores per subject."""
    assessment_weights = io.get_assessment_weights()
    totals: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"weighted": 0.0, "weight": 0.0})

    for entry in history:
        subject = str(entry.get("subject"))
        score = float(entry.get("score", 0.0))
        assessment_type = entry.get("type")

        weight = assessment_weights.get(str(assessment_type), 1.0)

        totals[subject]["weighted"] += score * weight
        totals[subject]["weight"] += weight

    return dict(totals)
