# Subject Recommender

Subject Recommender builds balanced study plans from assessment history and predicted grades stored in SQLite. It weights results by assessment type and recency, blends them with baseline predictions, and returns a session-by-session schedule together with run-level insights.

## Key Features
- Weighted scoring that combines assessment-type weights, time decay, and predicted grade fallbacks.
- Multi-shot plan generation that discourages immediate repeats, applies penalties for skipped subjects, shuffles subject order for output, and persists synthetic history entries.
- Configuration-first design: all tunables (weights, session timings, database defaults) live in `src/subject_recommender/config.py` and are consumed via IO helpers.
- Command-line entry point `subject-recommender` with an optional history reset flag.
- Data utilities for creating synthetic history from predictions and cleaning revision artifacts directly in SQLite.

## Repository Layout
- `README.md`, `agents.md`, `CHANGELOG.md`, `pyproject.toml`: docs and configuration.
- `data/`: SQLite database (`database.sqlite`), schema reference (`schema.txt`), and helper scripts (`generate_history_from_predicted.py`, `reset.py`, `migrate.py`).
- `src/subject_recommender/`: library code (`config.py`, `io.py`, `cli.py`, `history_reset.py`, `preprocessing/`, `sessions/`).
- `tests/`: unit tests mirroring the package surface.

## Data Inputs
- All data lives in `data/database.sqlite` (schema in `data/schema.txt`):
  - `users(uuid, username, role)` must contain the active user ID from `config.DATABASE_USER_ID`.
  - `types(uuid, type, weight)` seeds assessment labels and their weights (e.g. Revision 0.1, Homework 0.2, Quiz 0.3, Topic Test 0.4, Mock Exam 0.5, Exam 0.6).
  - `subjects(uuid, name)` lists the available subjects.
  - `predictedGrades(predictedGradeID, userID, subjectID, score)` holds predicted grades (0–1) per subject for the configured user.
  - `history(historyEntryID, userID, subjectID, typeID, score, studied_at)` stores study history with scores and ISO dates.
- Date weighting uses `DATE_WEIGHT_ZERO_DAY_THRESHOLD`, `DATE_WEIGHT_MIN`, and `DATE_WEIGHT_MAX` from `config.py` to decay the impact of older results.

## How the Pipeline Works
1. **Weighting (`preprocessing.weighting`)**: applies assessment weights, adds a recency factor, and falls back to predicted grades when scores are non-positive.
2. **Aggregation (`preprocessing.aggregation`)**: averages weighted totals, favouring weighted results when they exist and flooring combined scores to two decimal places.
3. **Normalisation (`preprocessing.normalisation`)**: scales scores so they sum to one and selects the lowest-scoring subject as the next recommendation.
4. **Session generation (`sessions.generator`)**: runs the pipeline for `SESSION_COUNT` sessions per shot, boosts the chosen subject to avoid repeats, appends revision entries plus penalties for skipped subjects, persists the new history, shuffles subject order for display, and can repeat for multiple shots.
5. **CLI analysis (`cli.analyse_run`)**: reports shots executed, total sessions scheduled, unique subjects, and subject frequency.

## Usage
### Install
```
python -m venv .venv
. .venv/Scripts/activate   # On Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e .[dev]
```

### Run the recommender
```
subject-recommender
```
The command reads the configured database, prints each shot’s schedule (shuffled subjects), and appends `Revision`/`Not Studied` entries to the history table. To reset the history after a run, add `--reset`:
```
subject-recommender --reset
```
You can also run directly via Python: `python -m subject_recommender.cli`.

### Programmatic use
```python
from subject_recommender.sessions import generate_session_plan

plans = generate_session_plan()  # uses configured data and session defaults
for plan in plans:
    print(plan.subjects)
```
Override inputs by passing a custom history sequence, session parameters (`count`, `session_time`, `break_time`, `shots`), or `session_date`.

## Data Utilities
- `src/subject_recommender/history_reset.py` and `data/reset.py`: delete `Revision` and `Not Studied` entries from the history table for the configured user.
- `data/generate_history_from_predicted.py`: create synthetic history entries from predicted grades stored in SQLite (optional `--user-id`/`--database` overrides).
- `data/migrate.py`: import legacy JSON predicted/history datasets into the SQLite schema for a specified user ID.

## Tests and Quality
- Unit tests: `pytest -q`
- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy src`

## Licence
This project is released under the Creative Commons Attribution-NonCommercial 4.0 International licence (see `LICENSE`). You may share and adapt the work non-commercially with attribution. For commercial licensing or other terms, contact rajveer@sandhuhome.uk.
