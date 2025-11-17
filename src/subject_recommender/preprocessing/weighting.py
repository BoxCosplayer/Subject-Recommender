"""Apply assessment weights to historical grade entries.

Purpose:
    Provide helpers for weighting historical assessment entries prior to
    aggregation further along the preprocessing pipeline.
Inputs:
    History entries retrieved from persistent storage via ``io``
    helpers, structured as mappings containing string keys for
    ``subject``, ``score``, and ``type``.
Outputs:
    Weighted history dictionaries keyed by subject name so that later
    preprocessing stages can combine and normalise scores consistently.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from math import floor

from .. import io

HistoryEntry = Mapping[str, float | str]
WeightedHistory = dict[str, dict[str, float]]  # {"subject": {"weighted": float, "weight": float}}


def apply_weighting(history: Iterable[HistoryEntry]) -> WeightedHistory:
    """Return running totals of weighted scores per subject.

    Inputs:
        history (Iterable[HistoryEntry]): Ordered or unordered collection
            of mappings representing historical assessment entries.
    Outputs:
        WeightedHistory: Dict keyed by subject with running weighted
            score totals and accumulated weights for each subject.
    """
    assessment_weights = io.get_assessment_weights()
    predicted_grades = io.get_predicted_grades()
    totals: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"weighted": 0.0, "weight": 0.0})

    for entry in history:
        subject = str(entry.get("subject"))
        score = float(entry.get("score", 0.0))
        assessment_type = entry.get("type")

        weight = assessment_weights.get(str(assessment_type), 0.0)

        if score > 0:
            weight *= 100 - score
            # print("POSITIVE - " + str(weight))
        else:
            predicted_grade = predicted_grades.get(subject, 0.1)
            prediction_delta = 1.0 - predicted_grade
            weight = floor(100 * prediction_delta)
            # if subject == "History":
            #     print("HIST - " + str(prediction_delta))
            #     print("HIST - " + str((100 * prediction_delta)))
            #     print("HIST - " + str(weight))
            # if subject == "Chemistry":
            #     print("CHEM - " + str(prediction_delta))
            #     print("CHEM - " + str((100 * prediction_delta)))
            #     print("CHEM - " + str(weight))

        totals[subject]["weighted"] += score * weight
        totals[subject]["weight"] += weight

    return dict(totals)
