"""Provide reusable helpers to clean study-history entries stored in SQLite.

Inputs: Database path and user identifier sourced from configuration via `io`.
Outputs: Deleted row counts and printed status messages after removing unwanted entries.
"""

from __future__ import annotations

from . import io

_EXCLUDED_TYPES = ("Revision", "Not Studied")


def filter_history() -> int:
    """Delete revision and not-studied entries for the configured user.

    Inputs: None directly; relies on `io` for database connection details.
    Outputs: int representing the number of deleted rows.
    """

    deleted = io.delete_history_by_types(_EXCLUDED_TYPES)
    return deleted


def main() -> None:
    """Execute the reset workflow for standalone usage.

    Inputs: None.
    Outputs: None: prints a short status message after deletion.
    """

    deleted = filter_history()
    print(
        f"Entries with type 'Revision' or 'Not Studied' have been removed from the history table. "
        f"{deleted} records deleted."
    )
