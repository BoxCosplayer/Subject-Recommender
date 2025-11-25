"""Migrate JSON-based subject data into the SQLite schema with user ownership.

Inputs:
    Command line arguments defining user_id (str), username (str), optional role (str),
    an optional database path (str | Path), and optional JSON source paths for
    predicted grades and study history.
Outputs:
    Side effects only: the SQLite database is populated or updated with users,
    subjects, types, predictedGrades, and history rows linked to the provided user_id.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from collections.abc import Iterable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from subject_recommender import config
except ModuleNotFoundError as exc:  # pragma: no cover - defensive for standalone use
    raise RuntimeError("The subject_recommender package could not be imported. Ensure SRC_DIR is on sys.path.") from exc

DEFAULT_DB_PATH = DATA_DIR / "database.sqlite"
DEFAULT_PREDICTED_FILE = getattr(config, "TEST_PREDICTED_GRADES_PATH", "gcse_test-predicted.json")
DEFAULT_HISTORY_FILE = getattr(config, "TEST_HISTORY_PATH", "gcse_test-grades.json")
NAMESPACE = uuid.UUID("4f5a8e32-d96f-4c8e-8f94-7b6e0de65c2d")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for the migration run.

    Inputs:
        None directly; values are read from sys.argv.
    Outputs:
        argparse.Namespace containing:
            user_id (str), username (str), role (str),
            database (Path), predicted_file (Path), history_file (Path).
    """

    parser = argparse.ArgumentParser(
        description=(
            "Load predicted grades and study history JSON files and write them into the "
            "SQLite database with deterministic identifiers and enforced foreign keys."
        )
    )
    parser.add_argument("--user-id", required=True, help="Unique identifier for the user the data will belong to.")
    parser.add_argument("--username", required=True, help="Username associated with the supplied user ID.")
    parser.add_argument("--role", default="student", help="Role to store for the user record; defaults to 'student'.")
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to the SQLite database file; defaults to {DEFAULT_DB_PATH}.",
    )
    parser.add_argument(
        "--predicted-file",
        type=Path,
        default=None,
        help=(
            "Path to the predicted grades JSON file. When omitted the configured "
            f"default {DEFAULT_PREDICTED_FILE} will be used relative to the data directory."
        ),
    )
    parser.add_argument(
        "--history-file",
        type=Path,
        default=None,
        help=(
            "Path to the study history JSON file. When omitted the configured "
            f"default {DEFAULT_HISTORY_FILE} will be used relative to the data directory."
        ),
    )
    return parser.parse_args()


def resolve_data_path(candidate: Path | str | None, fallback: str) -> Path:
    """Resolve a candidate path or fallback string to an absolute location.

    Inputs:
        candidate (Path | str | None): Explicitly supplied path; may be absolute or relative
            to the current working directory.
        fallback (str): Default relative filename when candidate is None; resolved under data/.
    Outputs:
        Path: Absolute path to the target dataset.
    """

    if candidate is not None:
        return Path(candidate).expanduser().resolve()

    fallback_path = Path(fallback)
    if fallback_path.is_absolute():
        return fallback_path
    return (DATA_DIR / fallback_path).resolve()


def load_predicted_scores(predicted_path: Path) -> dict[str, float]:
    """Load predicted grades into a subject-to-score mapping.

    Inputs:
        predicted_path (Path): Location of the JSON file containing predicted scores
            either as a mapping or a list of mappings.
    Outputs:
        dict[str, float]: Mapping of subject names to numeric scores.
    """

    with predicted_path.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)

    if isinstance(raw_data, dict):
        records: Iterable[dict[str, float]] = (raw_data,)
    elif isinstance(raw_data, list):
        records = raw_data
    else:
        raise ValueError("Predicted grades file must contain a dictionary or a list of dictionaries.")

    merged: dict[str, float] = {}
    for entry in records:
        if not isinstance(entry, dict):
            raise ValueError("Each predicted grade entry must be a JSON object.")
        for subject, value in entry.items():
            try:
                merged[subject] = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Predicted score for '{subject}' must be numeric.") from exc

    if not merged:
        raise ValueError("No predicted scores found in the supplied file.")

    return merged


def load_history(history_path: Path) -> list[dict[str, str | float]]:
    """Load study history records in the canonical dictionary format.

    Inputs:
        history_path (Path): Path to the JSON array of study history entries.
    Outputs:
        list[dict[str, str | float]]: Validated list of dictionaries with subject, type,
            score, and date keys.
    """

    with history_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError("History data must be a list of dictionaries.")

    normalised: list[dict[str, str | float]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("Each history entry must be an object.")
        normalised.append(
            {
                "subject": str(entry.get("subject", "")),
                "type": str(entry.get("type", "")),
                "score": float(entry.get("score", 0.0)),
                "date": str(entry.get("date", "")),
            }
        )

    if not normalised:
        raise ValueError("History data is empty; nothing to migrate.")

    return normalised


def initialise_schema(connection: sqlite3.Connection) -> None:
    """Create the required tables if they do not already exist.

    Inputs:
        connection (sqlite3.Connection): Open database connection with foreign keys enabled.
    Outputs:
        None directly; executes CREATE TABLE statements in the database.
    """

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS types (
            uuid TEXT PRIMARY KEY NOT NULL,
            type TEXT NOT NULL,
            weight REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            uuid TEXT PRIMARY KEY NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            uuid TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS predictedGrades (
            predictedGradeID TEXT PRIMARY KEY NOT NULL,
            userID TEXT NOT NULL,
            subjectID TEXT NOT NULL,
            score REAL NOT NULL,
            FOREIGN KEY (userID) REFERENCES users (uuid) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (subjectID) REFERENCES subjects (uuid) ON DELETE CASCADE ON UPDATE CASCADE
        );

        CREATE TABLE IF NOT EXISTS history (
            historyEntryID TEXT PRIMARY KEY NOT NULL,
            userID TEXT NOT NULL,
            subjectID TEXT NOT NULL,
            typeID TEXT NOT NULL,
            score REAL NOT NULL,
            studied_at DATETIME NOT NULL,
            FOREIGN KEY (userID) REFERENCES users (uuid) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (subjectID) REFERENCES subjects (uuid) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (typeID) REFERENCES types (uuid) ON DELETE CASCADE ON UPDATE CASCADE
        );
        """
    )


def upsert_user(
    connection: sqlite3.Connection,
    user_id: str,
    username: str,
    role: str,
) -> None:
    """Insert or update the user record that owns the migrated data.

    Inputs:
        connection (sqlite3.Connection): Active connection to the database.
        user_id (str): Unique identifier to store in users.uuid.
        username (str): Username associated with the user record.
        role (str): Role text for the user.
    Outputs:
        None; performs an UPSERT against the users table.
    """

    connection.execute(
        """
        INSERT INTO users (uuid, username, role)
        VALUES (?, ?, ?)
        ON CONFLICT(uuid) DO UPDATE SET
            username = excluded.username,
            role = excluded.role;
        """,
        (user_id, username, role),
    )


def upsert_lookup_table(connection: sqlite3.Connection, table: str, items: dict[str, str], value_column: str) -> None:
    """Insert or update lookup table entries for subjects.

    Inputs:
        connection (sqlite3.Connection): Database connection to execute against.
        table (str): Name of the lookup table (currently 'subjects').
        items (dict[str, str]): Mapping of display names to UUIDs.
        value_column (str): Column name holding the label (e.g. 'name').
    Outputs:
        None; rows are inserted or updated in place.
    """

    statement = (
        f"INSERT INTO {table} (uuid, {value_column}) VALUES (?, ?)"
        f" ON CONFLICT(uuid) DO UPDATE SET {value_column} = excluded.{value_column};"
    )
    rows = [(uuid, name) for name, uuid in items.items()]
    connection.executemany(statement, rows)


def build_deterministic_id(prefix: str, *parts: str | float) -> str:
    """Create a deterministic UUID5 value from stringified parts and a prefix.

    Inputs:
        prefix (str): Label indicating the record type, included in the key material.
        *parts (str | float): Components that uniquely identify the record.
    Outputs:
        str: UUID5 derived from the configured namespace and supplied parts.
    """

    material = ":".join([prefix, *(str(part) for part in parts)])
    return str(uuid.uuid5(NAMESPACE, material))


def insert_predicted_grades(
    connection: sqlite3.Connection,
    user_id: str,
    predictions: dict[str, float],
    subject_ids: dict[str, str],
) -> int:
    """Insert predicted grades linked to the provided user and subjects.

    Inputs:
        connection (sqlite3.Connection): Database connection.
        user_id (str): User identifier owning the predicted grades.
        predictions (dict[str, float]): Subject names mapped to predicted scores.
        subject_ids (dict[str, str]): Mapping of subject names to subject UUIDs.
    Outputs:
        int: Number of predicted grade rows upserted.
    """

    rows: list[tuple[str, str, str, float]] = []
    for subject, score in predictions.items():
        subject_id = subject_ids[subject]
        predicted_id = build_deterministic_id("predicted", user_id, subject)
        rows.append((predicted_id, user_id, subject_id, float(score)))

    connection.executemany(
        """
        INSERT INTO predictedGrades (predictedGradeID, userID, subjectID, score)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(predictedGradeID) DO UPDATE SET
            userID = excluded.userID,
            subjectID = excluded.subjectID,
            score = excluded.score;
        """,
        rows,
    )
    return len(rows)


def insert_history_entries(
    connection: sqlite3.Connection,
    user_id: str,
    history: list[dict[str, str | float]],
    subject_ids: dict[str, str],
    type_ids: dict[str, str],
) -> int:
    """Insert history events with deterministic identifiers and relationships.

    Inputs:
        connection (sqlite3.Connection): Active database connection.
        user_id (str): User identifier owning the history entries.
        history (list[dict[str, str | float]]): Normalised list of history items.
        subject_ids (dict[str, str]): Mapping of subject names to UUIDs.
        type_ids (dict[str, str]): Mapping of type names to UUIDs.
    Outputs:
        int: Number of history rows upserted.
    """

    rows: list[tuple[str, str, str, str, float, str]] = []
    for entry in history:
        subject = str(entry["subject"])
        type_name = str(entry["type"])
        score = float(entry["score"])
        date = str(entry["date"])
        subject_id = subject_ids[subject]
        type_id = type_ids[type_name]
        history_id = build_deterministic_id("history", user_id, subject, type_name, date, score)
        rows.append((history_id, user_id, subject_id, type_id, score, date))

    connection.executemany(
        """
        INSERT INTO history (historyEntryID, userID, subjectID, typeID, score, studied_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(historyEntryID) DO UPDATE SET
            userID = excluded.userID,
            subjectID = excluded.subjectID,
            typeID = excluded.typeID,
            score = excluded.score,
            studied_at = excluded.studied_at;
        """,
        rows,
    )
    return len(rows)


def collect_subjects(
    predictions: dict[str, float],
    history: list[dict[str, str | float]],
) -> dict[str, str]:
    """Build deterministic ID maps for subjects from the datasets.

    Inputs:
        predictions (dict[str, float]): Subject-to-score mapping from predicted grades.
        history (list[dict[str, str | float]]): List of history entries containing subject labels.
    Outputs:
        dict[str, str]: subject_ids mapping names to UUID strings.
    """

    subject_names = set(predictions.keys()) | {str(entry["subject"]) for entry in history}
    return {name: build_deterministic_id("subject", name) for name in sorted(subject_names)}


def fetch_existing_types(connection: sqlite3.Connection) -> dict[str, str]:
    """Read the predefined types from the database and map names to UUIDs.

    Inputs:
        connection (sqlite3.Connection): Active database connection with a populated types table.
    Outputs:
        dict[str, str]: Mapping of type name to UUID present in the database.
    """

    cursor = connection.execute("SELECT uuid, type FROM types;")
    records = cursor.fetchall()
    if not records:
        raise RuntimeError("The types table is empty; seed it before running the migration.")
    return {row[1]: row[0] for row in records}


def main() -> None:
    """Coordinate loading JSON inputs and writing them into the SQLite database.

    Inputs:
        None directly; command line arguments control database paths and user metadata.
    Outputs:
        None explicitly; prints a short migration summary and populates the database.
    """

    args = parse_args()
    predicted_path = resolve_data_path(args.predicted_file, DEFAULT_PREDICTED_FILE)
    history_path = resolve_data_path(args.history_file, DEFAULT_HISTORY_FILE)

    predictions = load_predicted_scores(predicted_path)
    history = load_history(history_path)
    subject_ids = collect_subjects(predictions, history)

    args.database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.database) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        initialise_schema(connection)
        upsert_lookup_table(connection, "subjects", subject_ids, "name")
        type_ids = fetch_existing_types(connection)
        missing_types = {str(entry["type"]) for entry in history if str(entry["type"]) not in type_ids}
        if missing_types:
            raise ValueError(f"The following types are missing in the database: {sorted(missing_types)}")
        upsert_user(connection, args.user_id, args.username, args.role)
        predicted_count = insert_predicted_grades(connection, args.user_id, predictions, subject_ids)
        history_count = insert_history_entries(connection, args.user_id, history, subject_ids, type_ids)
        connection.commit()

    print(
        f"Migrated {predicted_count} predicted grades and {history_count} history entries for user '{args.username}' "
        f"into database at {args.database}."
    )


if __name__ == "__main__":
    main()
