"""Wrapper script to reset study-history rows in the SQLite database.

Inputs: None when executed directly; relies on configured database path and user ID.
Outputs: Printed status message indicating the number of deleted rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = _PROJECT_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from subject_recommender.history_reset import main as _package_main  # noqa: E402


def main() -> None:
    """Delegate to the packaged history reset helper for standalone execution."""

    _package_main()


if __name__ == "__main__":
    main()
