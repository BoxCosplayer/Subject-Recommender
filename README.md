# Subject Recommender

Subject Recommender builds balanced study plans from your assessment history and predicted grades. It weights results by assessment type and recency, blends them with baseline predictions, and returns a session-by-session schedule together with run-level insights.

## Key Features
- Weighted scoring that combines assessment-type weights, time decay, and predicted grade fallbacks.
- Multi-shot plan generation that discourages immediate repeats, applies penalties for skipped subjects, and persists synthetic history entries.
- Configuration-first design: all tunables (weights, session timings, dataset names) live in `src/subject_recommender/config.py` and are consumed via IO helpers.
- Command-line entry point `subject-recommender` with an optional history reset flag.
- Data utilities for creating synthetic history from predictions and cleaning revision artifacts.

## Repository Layout
- `README.md`, `agents.md`, `CHANGELOG.md`, `pyproject.toml`: docs and configuration.
- `data/`: sample datasets plus helper scripts (`gcse_test-*.json`, `alevel_test-*.json`, `generate_history_from_predicted.py`, `reset.py`).
- `src/subject_recommender/`: library code (`config.py`, `io.py`, `cli.py`, `history_reset.py`, `preprocessing/`, `sessions/`).
- `tests/`: unit tests mirroring the package surface (`test_preprocessing.py`, `test_sessions.py`, `test_cli.py`, etc.).

## Data Inputs
- Predicted grades: defaults to `data/gcse_test-predicted.json`. The file may be a single dictionary or a list containing one dictionary that maps subjects to scores between 0 and 1.
- Study history: defaults to `data/gcse_test-grades.json`, a list of entries with `subject`, `type`, `score`, and `date` (ISO `YYYY-MM-DD`). Scores are expected to be recorded as percentages (0–100) for sensible weighting, though smaller decimals are still processed.
- Assessment types and default weights (from `config.py`): Revision 0.1, Homework 0.2, Quiz 0.3, Topic Test 0.4, Mock Exam 0.5, Exam 0.6. The generator also writes `Revision` and `Not Studied` entries automatically.
- Date weighting uses `DATE_WEIGHT_ZERO_DAY_THRESHOLD`, `DATE_WEIGHT_MIN`, and `DATE_WEIGHT_MAX` from `config.py` to decay the impact of older results.
- Adjust dataset filenames by editing `TEST_PREDICTED_GRADES_PATH` and `TEST_HISTORY_PATH` in `config.py`; all consumers resolve paths via `io.py`.

## How the Pipeline Works
1. **Weighting (`preprocessing.weighting`)**: applies assessment weights, adds a recency factor, and falls back to predicted grades when scores are non-positive.
2. **Aggregation (`preprocessing.aggregation`)**: averages weighted totals, favouring weighted results when they exist and flooring combined scores to two decimal places.
3. **Normalisation (`preprocessing.normalisation`)**: scales scores so they sum to one and selects the lowest-scoring subject as the next recommendation.
4. **Session generation (`sessions.generator`)**: runs the pipeline for `SESSION_COUNT` sessions per shot, boosts the chosen subject to avoid repeats, appends revision entries plus penalties for skipped subjects, persists the new history, and can repeat for multiple shots.
5. **CLI analysis (`cli.analyse_run`)**: reports frequency, streaks, first repeat position, suggested `SESSION_COUNT`, and normalised score similarity relative to the top subject.

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
The command reads the configured datasets, prints each shot’s schedule, and appends `Revision`/`Not Studied` entries back to the history file. To reset the history after a run, add `--reset`:
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
- `src/subject_recommender/history_reset.py` and `data/reset.py`: strip `Revision` and `Not Studied` entries from a history file; accepts an optional filename argument.
- `data/generate_history_from_predicted.py`: create synthetic history from a predicted grades file. Example: `python data/generate_history_from_predicted.py data/gcse_test-predicted.json --count 50 --output data/generated-grades.json`.

## Tests and Quality
- Unit tests: `pytest -q`
- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy src`

## Licence
This project is released under the Creative Commons Attribution-NonCommercial 4.0 International licence (see `LICENSE`). You may share and adapt the work non-commercially with attribution. For commercial licensing or other terms, contact rajveer@sandhuhome.uk.
