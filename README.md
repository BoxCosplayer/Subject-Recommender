# Subject Recommender

Data‑driven helper for students to decide what subject to study next. It combines your recent assessment results with baseline confidence for each subject to produce a short‑term study schedule and a running history.

## Overview

- Reads past results from `input-results.json`.
- Computes a weighted performance score per subject (heavier weight for higher‑stakes assessments; adjusts for distance from a target score).
- Blends performance with default “confidence/predicted grade” per subject.
- Produces a study plan by repeatedly selecting the lowest‑scoring subject and simulating learning gains.
- Appends a daily log to `output/history.md` and updates `output/results.json` with synthetic entries ("Revision" / "Not Studied") for future runs.

The repository currently includes a library skeleton (`src/subject_recommender`) and a runnable script in `tests/AlgoTesting.py` that drives the algorithm. A CLI entry point (`subject-recommender`) is reserved for future work.

## Project Structure

```
.
├─ src/subject_recommender/         # Library (CLI stub in place)
├─ tests/                           # Runnable scripts (algorithm + utilities)
│  ├─ AlgoTesting.py                # Main algorithm driver
│  └─ reset.py                      # Utility to clean synthetic results
├─ input-results.json               # Source results (you edit/maintain this)
├─ output/
│  ├─ results.json                  # Derived results with synthetic entries
│  └─ history.md                    # Appended study plan log
└─ pyproject.toml                   # Tooling: ruff, black, mypy, pytest config
```

## Input Data

`input-results.json` is an array of entries with this shape:

```json
[
  {
    "subject": "Maths",
    "type": "Quiz",
    "score": 85,
    "date": "2025-03-04"
  }
]
```

- Recognized types (with base weights in the algorithm): `Homework` (0.2), `Quiz` (0.3), `Topic Test` (0.4), `Mock Exam` (0.5), `Exam` (0.6). Entries are further up‑weighted the farther they are from the target score (80) to emphasize unusually strong/weak results.
- The algorithm also appends `Revision` and `Not Studied` entries to `output/results.json` after a run to reflect that day’s study plan; these are used in subsequent runs.
- Default subject “confidence/predicted grade” values are embedded in the algorithm driver and blended with recent results using `default_weight=0.7` and `result_weight=0.3`.

## How It Works (Algorithm)

1. For each result, compute a weighted contribution using the assessment type, then adjust weight by its distance from a target score (80).
2. Average per‑subject performance and normalize to 0–1.
3. Blend with per‑subject defaults: `0.7 * default + 0.3 * recent_performance`.
4. Generate a short plan by repeatedly choosing the lowest‑scoring subject, simulating a study session, and updating scores. Defaults in the driver script are:
   - Sessions: 13
   - Session time: 45 minutes
   - Break time: 15 minutes
5. Append the plan to `output/history.md` and update `output/results.json` with `Revision`/`Not Studied` markers dated today.

## Quickstart

Prerequisites: Python 3.9+

```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .[dev]

# Run the algorithm driver (reads input-results.json and writes to output/*)
python tests/AlgoTesting.py

# Optional: clean synthetic entries (Revision/Not Studied) from output/results.json
python tests/reset.py
```

Notes
- Edit `input-results.json` to reflect your latest assessments before running.
- `tests/AlgoTesting.py` prints the recommended subjects (one per line) and updates outputs.

## Development

The library and CLI scaffolding live under `src/subject_recommender/` (CLI stub to be implemented). Tooling is configured in `pyproject.toml`.

- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy src`
- Tests: `pytest -q` (the current algorithm is exercised by a runnable script rather than assertions)

## License

SubjectRecommender is currently licensed under [AGPL-3.0](./LICENSE).

The plans are to eventually dual-license this sofware once primary functionality is established.
The licensing placs are as follows:

- Community Edition: [AGPL-3.0](./LICENSE) — free to use, modify, and self-host. If you run a modified version as a service, you must release your modifications under the AGPL.
- Commercial License: available for teams who want to use Roundtable in commercial products or connect it to proprietary systems without open-sourcing changes. Includes support and additional terms.

To discuss a commercial licensing, contact: rajveer@sandhuhome.uk

## Roadmap / TODO

- Integrate date‑based weightings (recency decay).
- Environment‑configurable target grades per subject and overall.
- Convert the driver into a proper CLI (`subject-recommender`).
- Add genuine unit tests (pytest) around the scoring and scheduling.
- Improve variable names, structure, and inline documentation.

## Acknowledgements

Authored by Rajveer Sandhu.
