"""Tests covering the command-line interface helper.

Inputs: pytest fixtures (`capsys`, `monkeypatch`) along with SessionPlan instances.
Outputs: Assertions validating formatted strings and CLI printing.
"""

from __future__ import annotations

import pytest

from subject_recommender import cli
from subject_recommender.sessions.generator import SessionPlan


def test_format_plan_lists_subjects_in_order() -> None:
    """Ensure `_format_plan` enumerates subjects when sessions exist.

    Inputs: SessionPlan with two subjects, empty entries/history otherwise.
    Outputs: Text containing ordered bullet lines referencing each subject once.
    """

    plan = SessionPlan(subjects=["Maths", "History"], new_entries=[], history=[])

    formatted = cli._format_plan(plan, spin_number=1)

    assert "spin 1" in formatted
    assert "1. Maths" in formatted
    assert "2. History" in formatted


def test_format_plan_handles_empty_sessions() -> None:
    """Verify `_format_plan` reports when no sessions are scheduled.

    Inputs: SessionPlan with an empty subjects list.
    Outputs: String informing the user that no sessions were scheduled.
    """

    plan = SessionPlan(subjects=[], new_entries=[], history=[])

    assert cli._format_plan(plan) == "No study sessions scheduled."


def test_analyse_run_reports_frequency_and_patterns() -> None:
    """Ensure `analyse_run` captures frequency plus repeat positions."""

    plans = [SessionPlan(subjects=["Maths", "Maths", "History"], new_entries=[], history=[])]

    analysis = cli.analyse_run(plans)

    assert analysis["frequency"]["Maths"] == 2
    assert analysis["longest_streak"] == 2
    assert analysis["first_repeat_position"] == 2
    assert analysis["recommended_session_cap"] == 1
    assert analysis["spins"] == 1


def test_format_analysis_mentions_recommendation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify `_format_analysis` surfaces insights and config references."""

    plans = [SessionPlan(subjects=["Physics", "Chemistry", "Physics"], new_entries=[], history=[])]
    monkeypatch.setattr(cli.config, "SESSION_COUNT", 13)

    summary = cli._format_analysis(plans)

    assert "Overall session insights" in summary
    assert "Spins executed: 1" in summary
    assert "Subject frequency" in summary
    assert "First repeat detected at session 3" in summary
    assert "Suggested SESSION_COUNT cap" in summary


def test_format_analysis_handles_empty_run() -> None:
    """Ensure analysis formatter reports the absence of sessions."""

    plans = [SessionPlan(subjects=[], new_entries=[], history=[])]

    assert "No sessions to analyse" in cli._format_analysis(plans)


def test_main_prints_plan_and_analysis(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Confirm the CLI entry point prints both the plan and the insights."""

    plan = SessionPlan(subjects=["Physics", "Chemistry"], new_entries=[], history=[])
    monkeypatch.setattr(cli, "generate_session_plan", lambda: [plan])
    monkeypatch.setattr(cli.config, "SESSION_COUNT", 5)

    cli.main()

    captured = capsys.readouterr().out.strip()
    assert "Study session plan" in captured
    assert "Overall session insights" in captured
    assert "Suggested SESSION_COUNT cap" in captured


def test_main_handles_multiple_spins(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure the CLI prints each spin separately when multiple plans are generated."""

    plans = [
        SessionPlan(subjects=["Physics"], new_entries=[], history=[]),
        SessionPlan(subjects=["Chemistry"], new_entries=[], history=[]),
    ]
    monkeypatch.setattr(cli, "generate_session_plan", lambda: plans)
    monkeypatch.setattr(cli.config, "SESSION_COUNT", 5)

    cli.main()

    captured = capsys.readouterr().out.strip()
    assert "spin 1" in captured
    assert "spin 2" in captured
    assert "Overall session insights" in captured
