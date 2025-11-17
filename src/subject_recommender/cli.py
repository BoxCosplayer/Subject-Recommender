"""Provide a minimal command-line interface for generating a study plan.

Inputs: None supplied via CLI flags; the module reads persisted history/config.
Outputs: Printed list of subjects representing the generated session sequence and analysis.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from . import config
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


def analyse_run(plans: list[SessionPlan]) -> dict[str, Any]:
    """Return descriptive statistics for the full multi-shot run."""
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

    return {
        "frequency": dict(frequency),
        "unique_subjects": unique_subjects,
        "longest_streak_subject": longest_streak_subject,
        "longest_streak": longest_streak,
        "first_repeat_position": first_repeat_position,
        "recommended_session_cap": max(recommended_cap, 0),
        "total_sessions": len(subjects),
        "shots": len(plans),
    }


def _format_analysis(plans: list[SessionPlan]) -> str:
    """Return a human-readable string describing run-level statistics."""
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
        f"- Longest streak: {analysis['longest_streak_subject'] or 'N/A'} (×{analysis['longest_streak']})",
    ]

    if analysis["first_repeat_position"]:
        lines.append(
            f"- First repeat detected at session {analysis['first_repeat_position']}",
        )
    else:
        lines.append("- No repeated subjects within this run.")

    recommended_cap = analysis["recommended_session_cap"]
    lines.append(
        f"- Suggested SESSION_COUNT cap: {recommended_cap} (current: {config.SESSION_COUNT})",
    )

    return "\n".join(lines)


def main() -> None:
    """Entry point for the CLI executable.

    Inputs: None (relies on configuration defaults and stored history).
    Outputs: Printed study plan text and analysis streamed to standard output.
    """
    plans = generate_session_plan()
    for index, plan in enumerate(plans, start=1):
        print(_format_plan(plan, shot_number=index if len(plans) > 1 else None))

    print(_format_analysis(plans))
