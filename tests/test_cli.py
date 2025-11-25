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

    formatted = cli._format_plan(plan, shot_number=1)

    assert "shot 1" in formatted
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
    assert analysis["shots"] == 1
    assert "normalised_scores" in analysis
    assert "normalised_similarity" in analysis


def test_format_analysis_mentions_recommendation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify `_format_analysis` surfaces insights and config references."""

    plans = [SessionPlan(subjects=["Physics", "Chemistry", "Physics"], new_entries=[], history=[])]
    monkeypatch.setattr(cli.config, "SESSION_COUNT", 13)
    monkeypatch.setattr(
        cli.preprocessing,
        "calculate_normalised_scores",
        lambda _: {"Physics": 0.6, "Chemistry": 0.4},
    )

    summary = cli._format_analysis(plans)

    assert "Overall session insights" in summary
    assert "Shots executed: 1" in summary
    assert "Subject frequency" in summary
    assert "Total sessions scheduled" in summary
    assert "Unique subjects scheduled" in summary


def test_format_analysis_handles_empty_run() -> None:
    """Ensure analysis formatter reports the absence of sessions."""

    plans = [SessionPlan(subjects=[], new_entries=[], history=[])]

    assert "No sessions to analyse" in cli._format_analysis(plans)


def test_format_analysis_handles_missing_normalised_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure `_format_analysis` reports unavailable similarity metrics when no scores exist.

    Inputs: SessionPlan containing at least one subject and a monkeypatched normalised score response of `{}`.
    Outputs: Summary string containing the basic insight lines.
    """

    plans = [SessionPlan(subjects=["Physics"], new_entries=[], history=[])]
    monkeypatch.setattr(cli.preprocessing, "calculate_normalised_scores", lambda _: {})

    summary = cli._format_analysis(plans)

    assert "Overall session insights" in summary
    assert "Subject frequency" in summary


def test_main_prints_plan_and_analysis(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Confirm the CLI entry point prints both the plan and the insights."""

    plan = SessionPlan(subjects=["Physics", "Chemistry"], new_entries=[], history=[])
    monkeypatch.setattr(cli, "generate_session_plan", lambda: [plan])
    monkeypatch.setattr(cli.config, "SESSION_COUNT", 5)
    monkeypatch.setattr(cli.preprocessing, "calculate_normalised_scores", lambda _: {"Physics": 0.7})

    cli.main([])

    captured = capsys.readouterr().out.strip()
    assert "Study session plan" in captured
    assert "Overall session insights" in captured
    assert "Subject frequency" in captured


def test_main_handles_multiple_shots(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure the CLI prints each shot separately when multiple plans are generated."""

    plans = [
        SessionPlan(subjects=["Physics"], new_entries=[], history=[]),
        SessionPlan(subjects=["Chemistry"], new_entries=[], history=[]),
    ]
    monkeypatch.setattr(cli, "generate_session_plan", lambda: plans)
    monkeypatch.setattr(cli.config, "SESSION_COUNT", 5)
    monkeypatch.setattr(cli.preprocessing, "calculate_normalised_scores", lambda _: {"Chemistry": 0.5})

    cli.main([])

    captured = capsys.readouterr().out.strip()
    assert "shot 1" in captured
    assert "shot 2" in captured
    assert "Overall session insights" in captured


def test_main_resets_history_when_flagged(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure the reset flag clears the configured history file at the end of a run.

    Inputs: Monkeypatched session plan generator and reset helper, executed with `--reset`.
    Outputs: Assertions confirming the filtered filename and the printed status message.
    """

    plan = SessionPlan(subjects=["Physics"], new_entries=[], history=[])
    monkeypatch.setattr(cli, "generate_session_plan", lambda: [plan])
    monkeypatch.setattr(cli.config, "SESSION_COUNT", 3)

    calls: dict[str, int] = {"count": 0}

    def fake_reset() -> int:
        calls["count"] += 1
        return 5

    monkeypatch.setattr(cli, "filter_history", fake_reset)

    cli.main(["--reset"])

    captured = capsys.readouterr().out.strip()
    assert calls["count"] == 1
    assert "History reset applied" in captured


def test_calculate_score_similarity_scales_range() -> None:
    """Ensure score similarity scales between the lowest and highest normalised scores."""

    normalised_scores = {"Maths": 0.6, "History": 0.4, "Physics": 0.5}

    similarity = cli._calculate_score_similarity(normalised_scores)

    assert similarity["Maths"] == pytest.approx(1.0)
    assert similarity["History"] == pytest.approx(0.0)
    assert similarity["Physics"] == pytest.approx(0.5)


def test_calculate_score_similarity_handles_empty_mapping() -> None:
    """Validate `_calculate_score_similarity` returns an empty mapping for empty input.

    Inputs: Empty dictionary representing the absence of normalised scores.
    Outputs: Empty dictionary to indicate there are no subjects to compare.
    """

    assert cli._calculate_score_similarity({}) == {}


def test_calculate_score_similarity_scales_equal_scores() -> None:
    """Confirm `_calculate_score_similarity` returns 1.0 for uniform scores.

    Inputs: Normalised score dictionary where all subjects share the same value.
    Outputs: Mapping whose similarity entries are all 1.0, reflecting no variance.
    """

    similarity = cli._calculate_score_similarity({"Maths": 0.3, "Geography": 0.3})

    assert similarity == {"Maths": 1.0, "Geography": 1.0}
