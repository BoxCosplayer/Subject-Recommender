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
from datetime import date, datetime
from math import floor

from .. import io

HistoryEntry = Mapping[str, float | str]
WeightedHistory = dict[str, dict[str, float]]  # {"subject": {"weighted": float, "weight": float}}


def _calculate_date_weight(entry_date: str, weighting_config: dict[str, float | int], reference_date: date) -> float:
    """Return a decay factor based on how old a history entry is.

    Inputs:
        entry_date (str): ISO formatted date string (YYYY-MM-DD) for the entry.
        weighting_config (dict[str, float | int]): Mapping containing `min_weight`,
            `max_weight`, and `zero_day_threshold` bounds sourced from configuration.
        reference_date (date): The date to measure entry age against.
    Outputs:
        float: Date-derived multiplier clamped between configured min and max weights.
    """
    try:
        parsed_date = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return float(weighting_config["max_weight"])

    age_days = (reference_date - parsed_date).days
    decay_window = max(1, int(weighting_config["zero_day_threshold"]))
    min_weight = float(weighting_config["min_weight"])
    max_weight = float(weighting_config["max_weight"])

    if age_days >= decay_window:
        return min_weight
    if age_days <= 0:
        return max_weight

    span = max_weight - min_weight
    scaled_weight = max_weight - (span * (age_days / decay_window))
    return max(min_weight, min(max_weight, scaled_weight))


def apply_weighting(history: Iterable[HistoryEntry]) -> WeightedHistory:
    """Return running totals of weighted scores per subject.

    Inputs:
        history (Iterable[HistoryEntry]): Ordered or unordered collection
            of mappings representing historical assessment entries.
    Outputs:
        WeightedHistory: Dict keyed by subject with running weighted
            score totals and accumulated weights for each subject. Applies
            both assessment and date-based weighting to reflect recency.
    """
    assessment_weights = io.get_assessment_weights()
    date_weighting = io.get_date_weighting()
    predicted_grades = io.get_predicted_grades()
    totals: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"weighted": 0.0, "weight": 0.0})
    today = date.today()

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

        date_weight = _calculate_date_weight(str(entry.get("date", "")), date_weighting, today)
        weight *= date_weight

        totals[subject]["weighted"] += score * weight
        totals[subject]["weight"] += weight

    return dict(totals)
