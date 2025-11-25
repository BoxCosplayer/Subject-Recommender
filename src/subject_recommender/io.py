"""Expose configuration values and persisted datasets to the application.

Inputs: constants from `config.py` and SQLite records stored under `data/database.sqlite`.
Outputs: Dictionaries that modules such as preprocessing and sessions can consume directly. Acts
as the single database access layer for reads and writes.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from . import config


def _get_database_settings() -> tuple[Path, str]:
    """Return the configured database path and active user identifier.

    Inputs: None.
    Outputs: tuple[Path, str] describing the SQLite file location and user ID.
    """

    settings = config.get_database_settings()
    database_path = Path(settings["path"])
    user_id = str(settings["user_id"])
    return database_path, user_id


def _open_connection(database_path: Path) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enforced.

    Inputs: database_path (Path): location of the SQLite database file.
    Outputs: sqlite3.Connection with row_factory set for dict-like access.
    """

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def _get_type_map(connection: sqlite3.Connection, type_names: Iterable[str] | None = None) -> dict[str, str]:
    """Return a mapping of type names to UUIDs filtered by optional names.

    Inputs:
        connection (sqlite3.Connection): Active database connection.
        type_names (Iterable[str] | None): Optional iterable restricting the types returned.
    Outputs:
        dict[str, str]: Mapping of type names to their UUID identifiers.
    Raises:
        ValueError: when any requested type name is missing from the database.
    """

    if type_names is None:
        rows = connection.execute("SELECT uuid, type FROM types;").fetchall()
        return {row["type"]: row["uuid"] for row in rows}

    wanted = {name.strip() for name in type_names if name}
    placeholder = ",".join("?" for _ in wanted)
    rows = connection.execute(
        f"SELECT uuid, type FROM types WHERE type IN ({placeholder});",
        tuple(wanted),
    ).fetchall()
    found = {row["type"]: row["uuid"] for row in rows}
    missing = sorted(wanted - set(found))
    if missing:
        raise ValueError(f"Missing assessment types in database: {missing}")
    return found


def _get_subject_map(connection: sqlite3.Connection, subject_names: Iterable[str]) -> dict[str, str]:
    """Return a mapping of subject names to UUIDs, raising when any are missing.

    Inputs:
        connection (sqlite3.Connection): Active database connection.
        subject_names (Iterable[str]): Subject labels to look up.
    Outputs:
        dict[str, str]: Mapping of subject names to UUIDs.
    Raises:
        ValueError: when any supplied subject name is not found in the database.
    """

    names = {name.strip() for name in subject_names if name}
    if not names:
        return {}

    rows = connection.execute(
        f"SELECT uuid, name FROM subjects WHERE name IN ({','.join('?' for _ in names)});",
        tuple(names),
    ).fetchall()
    found = {row["name"]: row["uuid"] for row in rows}
    missing = sorted(names - set(found))
    if missing:
        raise ValueError(f"Missing subjects in database: {missing}")

    return found


def _assert_user_exists(connection: sqlite3.Connection, user_id: str) -> None:
    """Raise a ValueError when the configured user does not exist in the database."""

    row = connection.execute("SELECT 1 FROM users WHERE uuid = ? LIMIT 1;", (user_id,)).fetchone()
    if row is None:
        raise ValueError(f"User '{user_id}' does not exist in the database. Create the user before proceeding.")


def get_assessment_weights() -> dict[str, float]:
    """Return the weighting per assessment type sourced from the database.

    Inputs: None (derives database path and user from configuration).
    Outputs: dict[str, float] mapping assessment names to weights; falls back to config constants
    when the table is empty.
    """
    database_path, _ = _get_database_settings()
    with _open_connection(database_path) as connection:
        rows = connection.execute("SELECT type, weight FROM types;").fetchall()

    if rows:
        return {str(row["type"]): float(row["weight"]) for row in rows}

    return {
        "Revision": config.REVISION_WEIGHT,
        "Homework": config.HOMEWORK_WEIGHT,
        "Quiz": config.QUIZ_WEIGHT,
        "Topic Test": config.TOPIC_TEST_WEIGHT,
        "Mock Exam": config.MOCK_EXAM_WEIGHT,
        "Exam": config.EXAM_WEIGHT,
    }


def get_date_weighting() -> dict[str, float | int]:
    """Return age-based weighting boundaries for historical entries.

    Inputs: None.
    Outputs: dict[str, float | int] containing `min_weight`, `max_weight`,
    and `zero_day_threshold` for determining how entry age influences weight.
    """
    return {
        "min_weight": float(config.DATE_WEIGHT_MIN),
        "max_weight": float(config.DATE_WEIGHT_MAX),
        "zero_day_threshold": int(config.DATE_WEIGHT_ZERO_DAY_THRESHOLD),
    }


def get_session_defaults() -> dict[str, int]:
    """Return session parameters for session generation defaults.

    Inputs: None.
    Outputs: dict[str, int] describing session counts and timings.
    """
    return {
        "count": config.SESSION_COUNT,
        "session_time": config.SESSION_TIME_MINUTES,
        "break_time": config.BREAK_TIME_MINUTES,
        "shots": config.SHOTS,
    }


def get_predicted_grades() -> dict[str, float]:
    """Load predicted grades for the configured user from SQLite.

    Inputs: Database path and user ID derived from `config.get_database_settings()`.
    Outputs: dict[str, float] mapping subject names to predicted grade scores.
    Raises:
        ValueError: when no predicted grades are found for the configured user.
    """

    database_path, user_id = _get_database_settings()
    with _open_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT subjects.name AS subject_name, predictedGrades.score AS score
            FROM predictedGrades
            INNER JOIN subjects ON subjects.uuid = predictedGrades.subjectID
            WHERE predictedGrades.userID = ?
            """,
            (user_id,),
        ).fetchall()

    if not rows:
        raise ValueError(f"No predicted grades found for user '{user_id}'.")

    return {str(row["subject_name"]): float(row["score"]) for row in rows}


def get_study_history() -> list[dict[str, str | float]]:
    """Return the stored study history entries for the configured user.

    Inputs: Database path and user ID derived from `config.get_database_settings()`.
    Outputs: list[dict[str, str | float]] with the canonical history schema
    (`subject`, `type`, `score`, `date` fields). Returns an empty list when no history exists.
    """

    database_path, user_id = _get_database_settings()
    with _open_connection(database_path) as connection:
        _assert_user_exists(connection, user_id)
        rows = connection.execute(
            """
            SELECT
                subjects.name AS subject,
                types.type AS type,
                history.score AS score,
                history.studied_at AS date
            FROM history
            INNER JOIN subjects ON subjects.uuid = history.subjectID
            INNER JOIN types ON types.uuid = history.typeID
            WHERE history.userID = ?
            ORDER BY history.studied_at DESC;
            """,
            (user_id,),
        ).fetchall()

    return [
        {
            "subject": str(row["subject"]),
            "type": str(row["type"]),
            "score": float(row["score"]),
            "date": str(row["date"]),
        }
        for row in rows
    ]


def append_history_entries(entries: Sequence[Mapping[str, str | float]]) -> int:
    """Persist history entries for the configured user, creating subjects as required.

    Inputs:
        entries (Sequence[Mapping[str, str | float]]): Iterable of history entry dictionaries containing
            `subject`, `type`, `score`, and `date` keys.
    Outputs:
        int: Number of history rows written to the database.
    Raises:
        ValueError: when required assessment types are missing or the configured user does not exist.
    """

    if not entries:
        return 0

    database_path, user_id = _get_database_settings()
    with _open_connection(database_path) as connection:
        _assert_user_exists(connection, user_id)
        subjects = {str(entry.get("subject", "")).strip() for entry in entries if entry.get("subject")}
        types = {str(entry.get("type", "")).strip() for entry in entries if entry.get("type")}

        type_ids = _get_type_map(connection, types)
        subject_ids = _get_subject_map(connection, subjects)

        rows: list[tuple[str, str, str, str, float, str]] = []
        for entry in entries:
            subject = str(entry.get("subject", "")).strip()
            type_name = str(entry.get("type", "")).strip()
            score = float(entry.get("score", 0.0))
            date_value = str(entry.get("date", ""))
            if not subject or not type_name:
                continue
            subject_id = subject_ids[subject]
            type_id = type_ids[type_name]
            history_id = str(uuid.uuid4())
            rows.append((history_id, user_id, subject_id, type_id, score, date_value))

        if not rows:
            return 0

        connection.executemany(
            """
            INSERT INTO history (historyEntryID, userID, subjectID, typeID, score, studied_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            rows,
        )
        connection.commit()

    return len(rows)


def delete_history_by_types(type_names: Iterable[str]) -> int:
    """Delete history entries for the configured user filtered by assessment types.

    Inputs:
        type_names (Iterable[str]): Assessment type labels to remove (e.g. ["Revision"]).
    Outputs:
        int: Number of deleted rows.
    """

    database_path, user_id = _get_database_settings()
    with _open_connection(database_path) as connection:
        _assert_user_exists(connection, user_id)
        type_ids = _get_type_map(connection, type_names)
        placeholder = ",".join("?" for _ in type_ids)
        parameters = (*type_ids.values(), user_id)
        cursor = connection.execute(
            f"DELETE FROM history WHERE typeID IN ({placeholder}) AND userID = ?;",
            parameters,
        )
        connection.commit()
        return cursor.rowcount
