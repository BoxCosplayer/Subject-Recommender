"""Wrapper script to reset study-history files without relying on package imports.

Inputs: Optional filename (str) under `data/` when executed directly; defaults to the configured dataset.
Outputs: Filtered history JSON persisted back to disk and a printed status message.
"""

from __future__ import annotations

import sys
from pathlib import Path

from subject_recommender.history_reset import filter_history_file  # type: ignore  # noqa: E402
from subject_recommender.history_reset import main as _package_main

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))


def main(file_name: str | None = None) -> None:
    """Delegate to the packaged history reset helper for standalone execution.

    Inputs: file_name (str | None): optional dataset name; if omitted, the configured default is used.
    Outputs: None: writes filtered history to disk and prints a short status message.
    """
    if file_name is None:
        _package_main()
        return
    filtered_data = filter_history_file(file_name)
    print(
        f"Entries with type 'Revision' or 'Not Studied' have been removed from {file_name}. "
        f"{len(filtered_data)} records remain."
    )


if __name__ == "__main__":
    main()
