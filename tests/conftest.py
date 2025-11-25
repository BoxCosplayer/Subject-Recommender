"""Provide shared test fixtures that detach tests from repository data files.

Inputs: pytest fixture machinery along with module references for monkeypatching.
Outputs: Auto-used fixtures that supply temporary datasets and patch configuration defaults.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

import pytest

from subject_recommender import config


@pytest.fixture(autouse=True)
def temporary_database(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create and configure an isolated SQLite database for all tests.

    Inputs: `monkeypatch` for swapping module attributes and `tmp_path_factory` for generating a temporary folder.
    Outputs: Path to the created database file with core tables and seed data populated.
    """

    data_dir = tmp_path_factory.mktemp("data")
    db_path = Path(data_dir, "database.sqlite")
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE users (uuid TEXT PRIMARY KEY NOT NULL, username TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE subjects (uuid TEXT PRIMARY KEY NOT NULL, name TEXT NOT NULL);
        CREATE TABLE types (uuid TEXT PRIMARY KEY NOT NULL, type TEXT NOT NULL, weight REAL NOT NULL);
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

    connection.execute("INSERT INTO users (uuid, username, role) VALUES ('fixture-user', 'tester', 'student');")

    type_seeds: Iterable[tuple[str, str, float]] = (
        ("type-revision", "Revision", 0.1),
        ("type-homework", "Homework", 0.2),
        ("type-quiz", "Quiz", 0.3),
        ("type-topic", "Topic Test", 0.4),
        ("type-mock", "Mock Exam", 0.5),
        ("type-exam", "Exam", 0.6),
        ("type-not-studied", "Not Studied", 0.0),
    )
    connection.executemany("INSERT INTO types (uuid, type, weight) VALUES (?, ?, ?);", type_seeds)

    connection.execute("INSERT INTO subjects (uuid, name) VALUES ('sub-maths', 'Maths');")
    connection.execute(
        """INSERT INTO predictedGrades (predictedGradeID, userID, subjectID, score) 
        VALUES ('pred-1','fixture-user','sub-maths',0.5);"""
    )
    connection.execute(
        "INSERT INTO history (historyEntryID, userID, subjectID, typeID, score, studied_at) VALUES "
        "('hist-1','fixture-user','sub-maths','type-quiz',50,'2025-01-01');"
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    monkeypatch.setattr(config, "DATABASE_USER_ID", "fixture-user")

    return db_path
