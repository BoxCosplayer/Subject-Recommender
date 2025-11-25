"""Generate study session plans by iterating the preprocessing pipeline.

Inputs: Historical assessment entries plus session parameters describing
the number of iterations and timing details.
Outputs: `SessionPlan` objects containing the ordered subjects and any history
entries that should be appended for persistence.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from math import sin

from .. import io, preprocessing
from ..preprocessing.weighting import HistoryEntry


@dataclass(slots=True)
class SessionPlan:
    """Immutable representation of a generated study plan.

    Attributes:
        subjects: Shuffled list[str] representing which subject to study per session.
        new_entries: list[dict[str, str | float]] describing synthetic history rows.
        history: list[dict[str, str | float]] representing the base history plus new entries.
    """

    subjects: list[str]
    new_entries: list[dict[str, str | float]]
    history: list[dict[str, str | float]]


def generate_session_plan(
    history: Sequence[HistoryEntry] | None = None,
    session_parameters: Mapping[str, int] | None = None,
    session_date: str | None = None,
    shots: int | None = None,
) -> list[SessionPlan]:
    """Return one or more study plans, optionally running multiple shots per invocation.

    Inputs:
        history: Sequence of history entries to seed the pipeline. Defaults to `io.get_study_history`.
        session_parameters: Mapping with `count`, `session_time`, `break_time`, and optionally `shots`.
        session_date: Optional ISO-formatted date string for new entries (defaults to today).
        shots: Optional override controlling how many sequential plans to generate.
    Outputs:
        list[SessionPlan] ordered by shot execution.
    """
    local_history = _prepare_history(history)
    parameters = _resolve_session_parameters(session_parameters)
    shot_count = shots if shots is not None else parameters.get("shots", 1)
    shot_count = max(int(shot_count or 1), 1)
    run_date = session_date or date.today().isoformat()

    plans: list[SessionPlan] = []
    for _ in range(shot_count):
        plan = _run_single_plan(
            local_history=local_history,
            session_parameters=parameters,
            session_date=run_date,
        )
        plans.append(plan)

    return plans


def _prepare_history(history: Sequence[HistoryEntry] | None) -> list[dict[str, str | float]]:
    """Return a mutable copy of the supplied or persisted study history.

    Inputs: Optional sequence of history entries; falls back to `io.get_study_history`.
    Outputs: list of dictionaries safe to mutate within the generator.
    """
    source_history = history if history is not None else io.get_study_history()
    return [dict(entry) for entry in source_history]


def _resolve_session_parameters(
    overrides: Mapping[str, int] | None,
) -> dict[str, int]:
    """Merge overrides with configuration defaults for session generation.

    Inputs: Optional mapping overriding `count`, `session_time`, and `break_time`.
    Outputs: Dict containing the resolved integer values for each parameter.
    """
    parameters = dict(io.get_session_defaults())

    if overrides:
        for key in ("count", "session_time", "break_time", "shots"):
            if key in overrides:
                parameters[key] = int(overrides[key])

    if "shots" not in parameters:
        parameters["shots"] = 1

    return parameters


def _build_revision_entry(
    subject: str,
    session_time: int,
    break_time: int,
    session_date: str,
) -> dict[str, str | float]:
    """Create the synthetic revision entry appended after each session.

    Inputs:
        subject: The subject label selected by the pipeline.
        session_time: Duration of the study slot (minutes).
        break_time: Break duration (minutes) to subtract from the score.
        session_date: ISO formatted date string to record against the entry.
    Outputs: Dictionary representing the history entry consumed by preprocessing.
    """
    predicted_grades = io.get_predicted_grades()
    predicted_grade = float(predicted_grades.get(subject, 0.0))
    x = math.fabs(predicted_grade - 1) * 2 * math.pi
    revision_score = float((sin(x / 4 + math.pi / 2)) * (session_time + break_time))
    return {
        "subject": subject,
        "type": "Revision",
        "score": revision_score,
        "date": session_date,
    }


def _initialise_local_scores(history: Sequence[HistoryEntry]) -> dict[str, float]:
    """Return per-subject scores scaled similarly to `tests/AlgoTesting.py`.

    Inputs: Sequence of history entries forwarded from `_prepare_history`.
    Outputs: dict[str, float] whose values represent blended scores / 100.
    """
    weighted = preprocessing.weighting.apply_weighting(history)
    aggregated = preprocessing.aggregation.aggregate_scores(weighted)
    return {subject: score / 100 for subject, score in aggregated.items()}


def _adjust_local_scores(
    local_scores: dict[str, float],
    chosen_subject: str,
    session_time: int,
    break_time: int,
) -> None:
    """Mutate the local score dictionary to discourage repeated selections.

    Inputs: Local score mapping used for subject selection, the chosen subject identifier,
    and the session timings (minutes).
    Outputs: None (side-effect updates `local_scores` in place).
    """
    studied_delta = 0.005 * (2.5 * session_time + break_time)
    not_studied_delta = 0.005

    for subject in local_scores:
        if subject == chosen_subject:
            local_scores[subject] += studied_delta
        else:
            local_scores[subject] = max(local_scores[subject] - not_studied_delta, 0.0)


def _collect_subjects(history: Sequence[HistoryEntry]) -> set[str]:
    """Return the set of tracked subjects across history and predicted grades.

    Inputs: history (Sequence[HistoryEntry]): entries containing subject identifiers.
    Outputs: set[str]: unique, non-empty subject labels pulled from history and predictions.
    """
    subjects = {str(entry.get("subject", "")).strip() for entry in history if entry.get("subject")}
    subjects.update(io.get_predicted_grades().keys())
    return {subject for subject in subjects if subject}


def _calculate_predicted_grades_from_history(
    history: Sequence[HistoryEntry],
) -> dict[str, float]:
    """Return predicted grades derived from weighted history averages.

    Inputs: history (Sequence[HistoryEntry]): study history entries used to compute per-subject averages.
    Outputs: dict[str, float]: mapping of subjects to predicted grades scaled between zero and one,
    ignoring negative scores and applying assessment weighting factors.
    """
    assessment_weights = io.get_assessment_weights()
    totals: dict[str, float] = {}
    weight_totals: dict[str, float] = {}
    tracked_subjects: set[str] = set()

    for entry in history:
        subject = str(entry.get("subject", "")).strip()
        if not subject:
            continue
        tracked_subjects.add(subject)
        score = float(entry.get("score", 0.0))
        if score < 0:
            continue
        assessment_type = str(entry.get("type", "")).strip()
        weight = float(assessment_weights.get(assessment_type, 0.0))
        if weight <= 0:
            continue
        totals[subject] = totals.get(subject, 0.0) + (score * weight)
        weight_totals[subject] = weight_totals.get(subject, 0.0) + weight

    predicted_grades: dict[str, float] = {}
    for subject in sorted(tracked_subjects):
        average_score = totals.get(subject, 0.0) / max(weight_totals.get(subject, 0.0), 1.0)
        predicted_grades[subject] = max(min(average_score / 100, 1.0), 0.0)

    return predicted_grades


def _build_not_studied_entries(
    tracked_subjects: set[str],
    studied_subjects: Counter[str],
    session_time: int,
    break_time: int,
    session_date: str,
) -> list[dict[str, str | float]]:
    """Return penalty entries for subjects not selected in the generated plan.

    Inputs:
        tracked_subjects: All subjects known from history and prediction datasets.
        studied_subjects: Counter tracking subjects chosen during this plan run.
        session_time: Duration of the study session in minutes.
        break_time: Break duration in minutes used to scale the penalty.
        session_date: ISO-formatted date marking when the penalty is applied.
    Outputs: list[dict[str, str | float]] containing negative scoring entries.
    """
    predicted_grades = io.get_predicted_grades()
    entries: list[dict[str, str | float]] = []

    for subject in sorted(tracked_subjects):
        if subject in studied_subjects:
            # Already recorded via revision entries for each study session.
            continue
        predicted_grade = float(predicted_grades.get(subject, 0.0))
        x = (1 - predicted_grade) * math.pi
        penalty_score = float(-sin(x) * (session_time + break_time))
        entries.append(
            {
                "subject": subject,
                "type": "Not Studied",
                "score": penalty_score,
                "date": session_date,
            }
        )

    return entries


def _shuffle_subjects(subjects: list[str]) -> list[str]:
    """Return a shuffled copy of the supplied subjects list for output display.

    Inputs: subjects (list[str]): ordered subjects selected during plan generation.
    Outputs: list[str]: shuffled copy to reduce positional predictability.
    """
    shuffled = list(subjects)
    random.shuffle(shuffled)
    return shuffled


def _persist_history(new_entries: Sequence[dict[str, str | float]]) -> None:
    """Append newly generated entries to the persisted history dataset.

    Inputs: Sequence of history entry dictionaries to persist into SQLite.
    Outputs: None (side-effect writes to the database via `io` helper).
    """
    if not new_entries:
        return

    io.append_history_entries(new_entries)


def _run_single_plan(
    local_history: list[dict[str, str | float]],
    session_parameters: Mapping[str, int],
    session_date: str,
) -> SessionPlan:
    """Execute the scheduling workflow for a single shot.

    Inputs:
        local_history: Mutable copy of the persisted or supplied study history.
        session_parameters: Mapping defining `count`, `session_time`, and `break_time`.
        session_date: ISO-formatted date string used for synthetic entries.
    Outputs: SessionPlan object containing ordered subjects and appended history rows.
    """
    session_count = max(int(session_parameters["count"]), 0)
    session_time = int(session_parameters["session_time"])
    break_time = int(session_parameters["break_time"])

    local_scores = _initialise_local_scores(local_history)
    tracked_subjects = _collect_subjects(local_history)

    subjects: list[str] = []
    session_entries: list[dict[str, str | float]] = []

    for _ in range(session_count):
        normalised_scores = preprocessing.normalisation.normalise_scores(local_scores)
        subject = preprocessing.normalisation.choose_lowest_subject(normalised_scores)
        subjects.append(subject)
        tracked_subjects.add(subject)

        entry = _build_revision_entry(
            subject=subject,
            session_time=session_time,
            break_time=break_time,
            session_date=session_date,
        )
        local_history.append(entry)
        session_entries.append(entry)
        _adjust_local_scores(
            local_scores=local_scores,
            chosen_subject=subject,
            session_time=session_time,
            break_time=break_time,
        )

    not_studied_entries = _build_not_studied_entries(
        tracked_subjects=tracked_subjects,
        studied_subjects=Counter(subjects),
        session_time=session_time,
        break_time=break_time,
        session_date=session_date,
    )
    local_history.extend(not_studied_entries)
    persisted_entries = session_entries + not_studied_entries

    plan = SessionPlan(
        subjects=_shuffle_subjects(subjects),
        new_entries=[dict(entry) for entry in persisted_entries],
        history=[dict(entry) for entry in local_history],
    )
    _persist_history(plan.new_entries)
    return plan
