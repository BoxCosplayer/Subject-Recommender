"""Provide reusable helpers to clean study-history datasets stored under `data/`.

Inputs: JSON filename (str) located in the repository's `data/` directory or an absolute path.
Outputs: list[dict[str, object]] persisted back to disk after filtering out revision-related entries.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_EXCLUDED_TYPES = {"Revision", "Not Studied"}
_DEFAULT_HISTORY_FILENAME = config.TEST_HISTORY_PATH


def _resolve_history_path(file_name: str) -> Path:
    """Return the absolute path to the targeted history dataset.

    Inputs: file_name (str): relative filename under `_DATA_DIR` or an absolute path.
    Outputs: Path pointing to an existing history file; raises FileNotFoundError if missing.
    """
    candidate = Path(file_name)
    if not candidate.is_absolute():
        candidate = _DATA_DIR / candidate
    if not candidate.is_file():
        raise FileNotFoundError(f"History file not found at {candidate}")
    return candidate


def filter_history_file(file_name: str) -> list[dict[str, object]]:
    """Filter out synthetic revision entries from the specified history dataset.

    Inputs: file_name (str): target JSON dataset path to clean.
    Outputs: list[dict[str, object]] representing the filtered contents, written back to disk.
    """
    history_path = _resolve_history_path(file_name)
    with history_path.open("r", encoding="utf-8-sig") as handle:
        data: list[dict[str, object]] = json.load(handle)

    filtered_data = [entry for entry in data if entry.get("type") not in _EXCLUDED_TYPES]

    with history_path.open("w", encoding="utf-8") as handle:
        json.dump(filtered_data, handle, indent=4)

    return filtered_data


def main(file_name: str | None = None) -> None:
    """Execute the reset workflow for standalone usage.

    Inputs: file_name (str | None): optional dataset name; defaults to `_DEFAULT_HISTORY_FILENAME`.
    Outputs: None: writes filtered results to disk and prints a short status message.
    """
    target = file_name or _DEFAULT_HISTORY_FILENAME
    filtered_data = filter_history_file(target)
    print(
        f"Entries with type 'Revision' or 'Not Studied' have been removed from {target}. "
        f"{len(filtered_data)} records remain."
    )
