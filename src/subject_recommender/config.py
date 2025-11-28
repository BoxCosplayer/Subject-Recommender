"""Define tunable parameters and system constants for the subject recommender.

Inputs: None; module-level constants configured inside this file.
Outputs: Named constants consumed across the package for reproducible behaviour, including
database defaults for user identification and storage paths.
"""

from __future__ import annotations

from pathlib import Path

# FIXED Assessment weights
REVISION_WEIGHT = 0.1
HOMEWORK_WEIGHT = 0.2
QUIZ_WEIGHT = 0.3
TOPIC_TEST_WEIGHT = 0.4
MOCK_EXAM_WEIGHT = 0.5
EXAM_WEIGHT = 0.6

# Date weights
DATE_WEIGHT_ZERO_DAY_THRESHOLD = 300
DATE_WEIGHT_MIN = 0
DATE_WEIGHT_MAX = 1


# Default session parameters (CLI overrides can provide runtime values)
SESSION_TIME_MINUTES = 45
BREAK_TIME_MINUTES = 15
# should be set to ~75% of the no. subjects / topics
SESSION_COUNT = 8
# should be === session_count ?
SHOTS = 8

# DATABASE Defaults (overridable via CLI flags when invoking the tool)
DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "database.sqlite"
DATABASE_USER_ID = "1"


def get_database_settings() -> dict[str, str | Path]:
    """Return the default database configuration for the application.

    Inputs: None.
    Outputs: dict[str, str | Path] containing:
        - path: Path object pointing to the SQLite database file.
        - user_id: str identifier of the active user, sourced from the environment when set.
    """

    return {"path": DATABASE_PATH, "user_id": DATABASE_USER_ID}
