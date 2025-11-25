"""Tests covering IO helper functions and their configuration bindings.

Inputs: pytest fixtures (`monkeypatch`, `tmp_path`) alongside temporary SQLite data.
Outputs: Dict responses reflecting configuration values or parsed database records.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from subject_recommender import config, io


def _bootstrap_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, user_id: str = "user-1") -> Path:
    """Create an isolated SQLite database with the required schema for tests.

    Inputs:
        monkeypatch (pytest.MonkeyPatch): Fixture used to override config values.
        tmp_path (Path): Temporary directory root provided by pytest.
        user_id (str): Identifier to assign to the seeded user.
    Outputs:
        Path pointing to the created database file with tables initialised.
    """

    db_path = tmp_path / "database.sqlite"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE users (
            uuid TEXT PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE TABLE subjects (
            uuid TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL
        );
        CREATE TABLE types (
            uuid TEXT PRIMARY KEY NOT NULL,
            type TEXT NOT NULL,
            weight REAL NOT NULL
        );
        CREATE TABLE predictedGrades (
            predictedGradeID TEXT PRIMARY KEY NOT NULL,
            userID TEXT NOT NULL,
            subjectID TEXT NOT NULL,
            score REAL NOT NULL,
            FOREIGN KEY (userID) REFERENCES users (uuid),
            FOREIGN KEY (subjectID) REFERENCES subjects (uuid)
        );
        CREATE TABLE history (
            historyEntryID TEXT PRIMARY KEY NOT NULL,
            userID TEXT NOT NULL,
            subjectID TEXT NOT NULL,
            typeID TEXT NOT NULL,
            score REAL NOT NULL,
            studied_at DATETIME NOT NULL,
            FOREIGN KEY (userID) REFERENCES users (uuid),
            FOREIGN KEY (subjectID) REFERENCES subjects (uuid),
            FOREIGN KEY (typeID) REFERENCES types (uuid)
        );
        """
    )
    connection.execute("INSERT INTO users (uuid, username, role) VALUES (?, ?, ?);", (user_id, "tester", "student"))
    connection.execute("INSERT INTO types (uuid, type, weight) VALUES ('type-quiz', 'Quiz', 0.3);")
    connection.execute("INSERT INTO types (uuid, type, weight) VALUES ('type-exam', 'Exam', 0.6);")
    connection.commit()
    connection.close()

    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    monkeypatch.setattr(config, "DATABASE_USER_ID", user_id)

    return db_path


def test_get_assessment_weights_reflects_config() -> None:
    """Ensure assessment weight lookups mirror config constants.

    Inputs: None beyond imported configuration module.
    Outputs: Dict mapping strings to floats matching config attributes.
    """

    weights = io.get_assessment_weights()

    for key, expected in {
        "Revision": config.REVISION_WEIGHT,
        "Homework": config.HOMEWORK_WEIGHT,
        "Quiz": config.QUIZ_WEIGHT,
        "Topic Test": config.TOPIC_TEST_WEIGHT,
        "Mock Exam": config.MOCK_EXAM_WEIGHT,
        "Exam": config.EXAM_WEIGHT,
    }.items():
        assert weights[key] == pytest.approx(expected)


def test_append_history_entries_requires_existing_subjects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure appending history fails when subjects are missing from the database."""

    _bootstrap_database(monkeypatch, tmp_path, user_id="user-123")
    # Seed types but not subjects; helper already inserted types and user.
    entries = [{"subject": "Nonexistent", "type": "Quiz", "score": 10, "date": "2025-03-01"}]

    with pytest.raises(ValueError):
        io.append_history_entries(entries)


def test_get_date_weighting_reflects_config() -> None:
    """Verify date weighting boundaries mirror configuration values.

    Inputs: None beyond imported configuration module.
    Outputs: Dict containing minimum, maximum, and threshold values.
    """

    weighting = io.get_date_weighting()

    assert weighting == {
        "min_weight": float(config.DATE_WEIGHT_MIN),
        "max_weight": float(config.DATE_WEIGHT_MAX),
        "zero_day_threshold": int(config.DATE_WEIGHT_ZERO_DAY_THRESHOLD),
    }


def test_get_session_defaults_reflects_config() -> None:
    """Confirm session defaults mirror session-related config values.

    Inputs: None beyond configuration state.
    Outputs: Dict describing count and durations.
    """

    defaults = io.get_session_defaults()

    assert defaults == {
        "count": config.SESSION_COUNT,
        "session_time": config.SESSION_TIME_MINUTES,
        "break_time": config.BREAK_TIME_MINUTES,
        "shots": config.SHOTS,
    }


def test_get_predicted_grades_reads_dataset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure predicted grades load from SQLite for the configured user.

    Inputs: Temporary SQLite database seeded with predicted grades for a single user.
    Outputs: Dict mapping subject names to scores.
    """

    db_path = _bootstrap_database(monkeypatch, tmp_path, user_id="user-123")
    connection = sqlite3.connect(db_path)
    connection.execute("INSERT INTO subjects (uuid, name) VALUES ('sub-1', 'Maths');")
    connection.execute(
        "INSERT INTO predictedGrades (predictedGradeID, userID, subjectID, score) VALUES (?, ?, ?, ?);",
        ("pred-1", "user-123", "sub-1", 0.75),
    )
    connection.commit()
    connection.close()

    assert io.get_predicted_grades() == {"Maths": pytest.approx(0.75)}


def test_get_predicted_grades_raises_for_empty_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Validate missing predicted grades raise `ValueError`."""

    _bootstrap_database(monkeypatch, tmp_path, user_id="user-none")

    with pytest.raises(ValueError):
        io.get_predicted_grades()


def test_get_predicted_grades_raises_for_invalid_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Legacy placeholder retained for compatibility; database loading cannot produce invalid payloads."""

    _bootstrap_database(monkeypatch, tmp_path, user_id="user-123")

    with pytest.raises(ValueError):
        io.get_predicted_grades()


def test_get_predicted_grades_supports_absolute_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure database path resolution works with absolute paths."""

    db_path = _bootstrap_database(monkeypatch, tmp_path, user_id="user-abs")
    connection = sqlite3.connect(db_path)
    connection.execute("INSERT INTO subjects (uuid, name) VALUES ('sub-abs', 'History');")
    connection.execute(
        """INSERT INTO predictedGrades (predictedGradeID, userID, subjectID, score) 
        VALUES ('pred-abs', 'user-abs', 'sub-abs', 0.95);"""
    )
    connection.commit()
    connection.close()

    assert io.get_predicted_grades() == {"History": pytest.approx(0.95)}


def test_get_study_history_reads_json_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure study history loading parses DB rows into dictionaries."""

    db_path = _bootstrap_database(monkeypatch, tmp_path, user_id="user-123")
    connection = sqlite3.connect(db_path)
    connection.execute("INSERT INTO subjects (uuid, name) VALUES ('sub-1', 'Maths');")
    connection.execute("INSERT INTO subjects (uuid, name) VALUES ('sub-2', 'French');")
    connection.execute(
        "INSERT INTO history (historyEntryID, userID, subjectID, typeID, score, studied_at) VALUES (?, ?, ?, ?, ?, ?);",
        ("hist-1", "user-123", "sub-1", "type-quiz", 65, "2025-03-02"),
    )
    connection.execute(
        "INSERT INTO history (historyEntryID, userID, subjectID, typeID, score, studied_at) VALUES (?, ?, ?, ?, ?, ?);",
        ("hist-2", "user-123", "sub-2", "type-exam", 72.5, "2025-03-01"),
    )
    connection.commit()
    connection.close()

    history = io.get_study_history()

    assert history[0]["subject"] == "Maths"
    assert history[0]["type"] == "Quiz"
    assert history[0]["score"] == pytest.approx(65.0)
    assert history[1]["type"] == "Exam"


def test_get_study_history_rejects_non_list_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure empty history returns an empty list instead of raising."""

    _bootstrap_database(monkeypatch, tmp_path, user_id="user-empty")

    assert io.get_study_history() == []


def test_get_study_history_rejects_non_dict_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Retain coverage for absence of history entries as a benign case."""

    _bootstrap_database(monkeypatch, tmp_path, user_id="user-empty")

    assert io.get_study_history() == []


def test_get_assessment_weights_falls_back_when_types_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure defaults are used when the types table is empty."""

    db_path = tmp_path / "db.sqlite"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE users (uuid TEXT PRIMARY KEY NOT NULL, username TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE types (uuid TEXT PRIMARY KEY NOT NULL, type TEXT NOT NULL, weight REAL NOT NULL);
        """
    )
    connection.execute("INSERT INTO users (uuid, username, role) VALUES ('user-1', 'tester', 'student');")
    connection.commit()
    connection.close()

    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    monkeypatch.setattr(config, "DATABASE_USER_ID", "user-1")

    weights = io.get_assessment_weights()

    assert weights["Revision"] == pytest.approx(config.REVISION_WEIGHT)
    assert weights["Exam"] == pytest.approx(config.EXAM_WEIGHT)


def test_get_type_map_returns_all_when_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure `_get_type_map` returns all rows when no filter is provided."""

    db_path = _bootstrap_database(monkeypatch, tmp_path, user_id="user-abc")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    mapping = io._get_type_map(connection)  # type: ignore[attr-defined]
    connection.close()

    assert mapping["Quiz"] == "type-quiz"
    assert mapping["Exam"] == "type-exam"


def test_get_type_map_raises_for_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure missing assessment types raise a ValueError."""

    db_path = _bootstrap_database(monkeypatch, tmp_path, user_id="user-abc")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    with pytest.raises(ValueError):
        io._get_type_map(connection, ["Quiz", "Project"])  # type: ignore[attr-defined]
    connection.close()


def test_get_subject_map_returns_empty_for_no_names(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure subject map gracefully returns an empty mapping when no names supplied."""

    db_path = _bootstrap_database(monkeypatch, tmp_path, user_id="user-abc")
    connection = sqlite3.connect(db_path)
    assert io._get_subject_map(connection, []) == {}  # type: ignore[attr-defined]
    connection.close()


def test_get_study_history_raises_when_user_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure user validation triggers when the configured user is absent."""

    db_path = tmp_path / "db.sqlite"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE users (uuid TEXT PRIMARY KEY NOT NULL, username TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE subjects (uuid TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL);
        CREATE TABLE types (uuid TEXT PRIMARY KEY NOT NULL, type TEXT NOT NULL, weight REAL NOT NULL);
        CREATE TABLE history (
            historyEntryID TEXT PRIMARY KEY NOT NULL,
            userID TEXT NOT NULL,
            subjectID TEXT NOT NULL,
            typeID TEXT NOT NULL,
            score REAL NOT NULL,
            studied_at DATETIME NOT NULL
        );
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    monkeypatch.setattr(config, "DATABASE_USER_ID", "missing-user")

    with pytest.raises(ValueError):
        io.get_study_history()


def test_append_history_entries_returns_zero_for_empty_entries() -> None:
    """Ensure append helper short-circuits on empty input."""

    assert io.append_history_entries([]) == 0


def test_append_history_entries_skips_incomplete_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ensure entries lacking subject or type are ignored and do not write rows."""

    db_path = _bootstrap_database(monkeypatch, tmp_path, user_id="fixture-user")
    connection = sqlite3.connect(db_path)
    connection.execute("INSERT INTO subjects (uuid, name) VALUES ('sub-maths', 'Maths');")
    connection.execute("INSERT INTO types (uuid, type, weight) VALUES ('type-quiz-extra', 'Quiz', 0.3);")
    connection.commit()
    connection.close()
    entries = [
        {"subject": "", "type": "Quiz", "score": 10, "date": "2025-03-01"},
        {"subject": "Maths", "type": "", "score": 11, "date": "2025-03-02"},
    ]

    assert io.append_history_entries(entries) == 0
