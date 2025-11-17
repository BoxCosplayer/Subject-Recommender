"""Utility script to remove synthetic entries from `history.json`.

Inputs: JSON file stored alongside this script under `data/history.json`.
Outputs: Updated JSON file excluding entries whose `type` is `Revision` or `Not Studied`.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent
_HISTORY_PATH = _DATA_DIR / "results.json"


def main() -> None:
    """Load, filter, and rewrite the study history dataset."""
    with _HISTORY_PATH.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    filtered_data = [entry for entry in data if entry.get("type") not in {"Revision", "Not Studied"}]

    with _HISTORY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(filtered_data, handle, indent=4)

    print("Entries with type 'Revision' or 'Not Studied' have been removed.")


if __name__ == "__main__":
    main()
