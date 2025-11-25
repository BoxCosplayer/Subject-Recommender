"""Tests covering study history reset helpers backed by SQLite.

Inputs: Temporary SQLite database seeded via the autouse fixture.
Outputs: Assertions confirming deletion behaviour and messaging for excluded types.
"""

from __future__ import annotations

import sqlite3

import pytest

from subject_recommender import config, history_reset


def _count_history_entries() -> int:
    """Return the number of history rows for the configured user."""
    connection = sqlite3.connect(config.DATABASE_PATH)
    count = connection.execute(
        "SELECT COUNT(*) FROM history WHERE userID = ?;",
        (config.DATABASE_USER_ID,),
    ).fetchone()[0]
    connection.close()
    return int(count)


def test_filter_history_removes_revision_and_not_studied() -> None:
    """Ensure `filter_history` deletes excluded types for the configured user."""

    connection = sqlite3.connect(config.DATABASE_PATH)
    connection.execute(
        "INSERT INTO history (historyEntryID, userID, subjectID, typeID, score, studied_at) VALUES "
        "('hist-extra-1', ?, 'sub-maths', 'type-revision', 5, '2025-01-02'),"
        "('hist-extra-2', ?, 'sub-maths', 'type-not-studied', -2, '2025-01-03'),"
        "('hist-extra-3', ?, 'sub-maths', 'type-quiz', 70, '2025-01-04');",
        (config.DATABASE_USER_ID, config.DATABASE_USER_ID, config.DATABASE_USER_ID),
    )
    connection.commit()
    connection.close()

    deleted = history_reset.filter_history()

    assert deleted == 2
    assert _count_history_entries() == 2  # one existing seed + one quiz


def test_main_reports_deleted_count(capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure `main` prints the deleted row count."""

    deleted_before = _count_history_entries()
    history_reset.main()
    message = capsys.readouterr().out.strip()

    assert "Entries with type 'Revision' or 'Not Studied'" in message
    assert "records deleted" in message
    assert _count_history_entries() <= deleted_before
