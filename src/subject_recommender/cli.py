"""Provide a minimal command-line interface for generating a study plan.

Inputs: Optional CLI flags such as `-r/--reset` to clean configured history datasets and
runtime overrides for session timings, session counts, shot repetitions, and user selection.
Outputs: Printed list of subjects representing the generated session sequence and analysis.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from typing import Any

from . import config, preprocessing  # noqa: F401 - config imported for test patching
from .history_reset import filter_history
from .sessions import generate_session_plan
from .sessions.generator import SessionPlan


def _format_plan(plan: SessionPlan, shot_number: int | None = None) -> str:
    """Return a newline-delimited representation of a session plan.

    Inputs: `plan` (`SessionPlan`) containing the ordered subject list.
    Outputs: String ready for console display describing the schedule.
    """
    if not plan.subjects:
        return "No study sessions scheduled."

    header = "Study session plan"
    if shot_number is not None:
        header = f"{header} (shot {shot_number})"

    lines = [f"{header}:"]
    for index, subject in enumerate(plan.subjects, start=1):
        lines.append(f"{index}. {subject}")
    return "\n".join(lines)


def _calculate_score_similarity(normalised_scores: dict[str, float]) -> dict[str, float]:
    """Return per-subject similarity relative to the highest normalised score.

    Inputs: normalised_scores (dict[str, float]): mapping of subjects to normalised scores that
    should sum to one.
    Outputs: dict[str, float]: mapping of subjects to similarity ratios between zero (lowest score)
    and one (highest score) scaled across the observed score range.
    """
    if not normalised_scores:
        return {}

    max_score = max(normalised_scores.values())
    min_score = min(normalised_scores.values())

    if max_score == min_score:
        return {subject: 1.0 for subject in normalised_scores}

    spread = max_score - min_score
    return {subject: (score - min_score) / spread for subject, score in normalised_scores.items()}


def analyse_run(plans: list[SessionPlan]) -> dict[str, Any]:
    """Return descriptive statistics for the full multi-shot run.

    Inputs: plans (list[SessionPlan]): ordered study plans produced by the generator.
    Outputs: dict[str, Any]: aggregate metrics including frequency, streaks, recommendations,
    normalised scores, and similarity ratios describing how close subjects are to the highest score.
    """
    subjects = [subject for plan in plans for subject in plan.subjects]
    frequency = Counter(subjects)
    unique_subjects = len(frequency)

    longest_streak_subject: str | None = None
    longest_streak = 0
    current_subject: str | None = None
    current_length = 0

    for subject in subjects:
        if subject == current_subject:
            current_length += 1
        else:
            current_subject = subject
            current_length = 1

        if current_length > longest_streak:
            longest_streak = current_length
            longest_streak_subject = subject

    seen: set[str] = set()
    recommended_cap = 0
    first_repeat_position: int | None = None

    for index, subject in enumerate(subjects, start=1):
        if subject in seen:
            first_repeat_position = index
            recommended_cap = index - 1
            break
        seen.add(subject)
    else:
        recommended_cap = len(subjects)

    final_history = plans[-1].history if plans else []
    normalised_scores = preprocessing.calculate_normalised_scores(final_history)
    normalised_similarity = _calculate_score_similarity(normalised_scores)

    return {
        "frequency": dict(frequency),
        "unique_subjects": unique_subjects,
        "longest_streak_subject": longest_streak_subject,
        "longest_streak": longest_streak,
        "first_repeat_position": first_repeat_position,
        "recommended_session_cap": max(recommended_cap, 0),
        "total_sessions": len(subjects),
        "shots": len(plans),
        "normalised_scores": normalised_scores,
        "normalised_similarity": normalised_similarity,
    }


def _format_analysis(plans: list[SessionPlan]) -> str:
    """Return a human-readable string describing run-level statistics.

    Inputs: plans (list[SessionPlan]): ordered study plans to analyse.
    Outputs: str: formatted, multi-line analysis suitable for console output.
    """
    analysis = analyse_run(plans)
    if not analysis["total_sessions"]:
        return "\nNo sessions to analyse."

    frequency_items = sorted(
        analysis["frequency"].items(),
        key=lambda item: (-item[1], item[0]),
    )
    frequency_text = ", ".join(f"{subject}: {count}" for subject, count in frequency_items)

    lines = [
        "",
        "Overall session insights:",
        f"- Shots executed: {analysis['shots']}",
        f"- Total sessions scheduled: {analysis['total_sessions']}",
        f"- Unique subjects scheduled: {analysis['unique_subjects']}",
        f"- Subject frequency: {frequency_text}",
    ]

    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse recognised CLI arguments for the subject recommender command.

    Inputs: argv (Sequence[str] | None): optional argument list excluding the program name.
    Outputs: argparse.Namespace containing parsed flags such as `reset`, session defaults,
    and the active user identifier.
    """
    parser = argparse.ArgumentParser(description="Generate a study plan and supporting insights.")
    parser.add_argument(
        "-r",
        "--reset",
        action="store_true",
        help="Reset the configured history dataset after generating the plan.",
    )
    parser.add_argument(
        "-c",
        "--session-count",
        type=int,
        default=config.SESSION_COUNT,
        help="Number of study sessions to schedule per shot (defaults to configuration).",
    )
    parser.add_argument(
        "-t",
        "--session-time",
        type=int,
        default=config.SESSION_TIME_MINUTES,
        help="Duration of each study session in minutes (defaults to configuration).",
    )
    parser.add_argument(
        "-b",
        "--break-time",
        type=int,
        default=config.BREAK_TIME_MINUTES,
        help="Break duration in minutes to subtract when calculating scores (defaults to configuration).",
    )
    parser.add_argument(
        "-s",
        "--shots",
        type=int,
        default=config.SHOTS,
        help="Number of sequential shots (full plan runs) to execute (defaults to configuration).",
    )
    parser.add_argument(
        "-u",
        "--user-id",
        type=str,
        default=config.DATABASE_USER_ID,
        help="User identifier to target when reading and writing SQLite-backed data (defaults to configuration).",
    )
    return parser.parse_args(argv)


def _reset_history() -> int:
    """Invoke the data reset helper against the database-backed history.

    Inputs: None.
    Outputs: int representing the number of deleted rows.
    """
    deleted = filter_history()
    print("History reset applied to database-backed history.")
    return deleted


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for the CLI executable.

    Inputs: argv (Sequence[str] | None): optional arguments forwarded from the shell.
    Outputs: Printed study plan text and analysis streamed to standard output.
    """
    args = _parse_args(argv)
    config.DATABASE_USER_ID = str(args.user_id)
    session_parameters = {
        "count": args.session_count,
        "session_time": args.session_time,
        "break_time": args.break_time,
        "shots": args.shots,
    }

    plans = generate_session_plan(session_parameters=session_parameters, shots=args.shots)
    for index, plan in enumerate(plans, start=1):
        print(_format_plan(plan, shot_number=index if len(plans) > 1 else None))

    print(_format_analysis(plans))
    if args.reset:
        _reset_history()
