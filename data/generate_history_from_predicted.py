"""Generate synthetic history entries from predicted grades stored in SQLite.

Inputs:
    CLI arguments controlling event counts, score ranges, topic bias, optional user ID override,
    optional database path override, and random seed for reproducibility.
Outputs:
    History rows inserted into the configured SQLite database for the selected user, with a summary
    printed to stdout.
"""

from __future__ import annotations

import argparse
import datetime as dt
import random
import sys
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from subject_recommender import config, io  # noqa: E402

EVENT_TYPES: Sequence[str] = (
    "Homework",
    "Quiz",
    "Topic Test",
    "Mock Exam",
    "Exam",
    "Project",
)


def parse_args() -> argparse.Namespace:
    """Build and parse the command line arguments used by the script.

    Inputs:
        None directly; the function reads command line arguments via argparse.
    Outputs:
        argparse.Namespace containing generation parameters plus optional database overrides.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic grade history entries from predicted grades stored in SQLite. "
            "Scores are scaled between the requested minimum and maximum values, defaulting to 0.3-1.0."
        )
    )
    parser.add_argument("--user-id", type=str, help="Override the configured user ID for which to generate history.")
    parser.add_argument(
        "--database",
        type=Path,
        help="Optional SQLite database path; defaults to the configured `DATABASE_PATH`.",
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=5,
        help="Minimum number of history events generated per subject.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=12,
        help="Maximum number of history events generated per subject.",
    )
    parser.add_argument(
        "--average-offset",
        type=float,
        default=0.05,
        help=("Average reduction applied to the predicted grade when targeting the history score mean."),
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.3,
        help="Lower bound for generated scores.",
    )
    parser.add_argument(
        "--max-score",
        type=float,
        default=1.0,
        help="Upper bound for generated scores.",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=210,
        help="Number of days in the past to sample history dates from.",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        help="Optional integer seed to make generation deterministic.",
    )
    parser.add_argument(
        "-t",
        "--topics",
        type=str,
        default="false",
        help=(
            "Treat the predicted grades as topic metrics. Accepts boolean-like "
            "values such as 'true', 'false', 'yes', 'no', '1', or '0'."
        ),
    )
    return parser.parse_args()


def interpret_effective_boolean(value: str | bool, flag_name: str = "flag") -> bool:
    """Interpret a string flag as a boolean while retaining the raw storage.

    Inputs:
        value (str | bool): Value supplied via CLI or configuration that should
            behave like a boolean.
        flag_name (str): Friendly name used to clarify potential error messages.
    Outputs:
        bool: True when the value represents an affirmative option, otherwise False.
    """

    if isinstance(value, bool):
        return value
    if value is None:
        return False

    truthy = {"1", "true", "t", "yes", "y", "on", "topics", "topic"}
    falsy = {"0", "false", "f", "no", "n", "off", "subjects", "subject"}

    normalised = str(value).strip().lower()
    if normalised in truthy:
        return True
    if normalised in falsy:
        return False

    raise ValueError(f"Value '{value}' for '{flag_name}' could not be interpreted as a boolean.")


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a value so it stays within the provided bounds.

    Inputs:
        value (float): Value that may need to be constrained.
        lower (float): Minimum acceptable value.
        upper (float): Maximum acceptable value.
    Outputs:
        float: Clamped value that lies between lower and upper (inclusive).
    """

    return max(lower, min(upper, value))


def generate_dates(
    count: int,
    rng: random.Random,
    days_back: int,
    anchor: dt.date | None = None,
) -> list[str]:
    """Generate ISO formatted dates for each synthetic history event.

    Inputs:
        count (int): Number of dates to produce.
        rng (random.Random): Random number generator instance.
        days_back (int): Maximum number of days to look back from the anchor.
        anchor (datetime.date | None): Reference date; defaults to today.
    Outputs:
        List[str]: ISO formatted YYYY-MM-DD date strings ordered newest-first.
    """

    if count <= 0:
        return []

    base_date = anchor or dt.date.today()
    offsets = sorted(rng.randint(0, max(days_back, 1)) for _ in range(count))
    offsets.reverse()  # newest first
    return [(base_date - dt.timedelta(days=offset)).isoformat() for offset in offsets]


def calculate_scores(
    predicted_value: float,
    event_count: int,
    average_offset: float,
    min_score: float,
    max_score: float,
    rng: random.Random,
    topics_mode: bool = False,
) -> list[float]:
    """Create event scores biased around the predicted grade minus an offset.

    Inputs:
        predicted_value (float): Expected maximum performance for the subject.
        event_count (int): Number of events for which scores are required.
        average_offset (float): Value to subtract from predicted_value when
            setting the targeted mean history score.
        min_score (float): Smallest allowed score (>= 0.3 by default).
        max_score (float): Largest allowed score (<= 1.0 by default).
        rng (random.Random): Random number generator instance.
        topics_mode (bool): Signals whether topic metrics are in use, which
            increases downward bias for low predicted scores.
    Outputs:
        List[float]: Scores scaled according to the configuration constraints.
    """

    if event_count <= 0:
        return []

    bounded_predicted = clamp(predicted_value, min_score, max_score)
    bias_multiplier = 1.0
    if topics_mode and bounded_predicted < 0.7:
        severity_range = max(0.7 - min_score, 0.05)
        severity = (0.7 - bounded_predicted) / severity_range
        severity = max(0.0, min(1.0, severity))
        bias_multiplier += severity
    target_average = clamp(
        bounded_predicted - abs(average_offset) * bias_multiplier,
        min_score,
        max_score,
    )
    std_dev = max((max_score - min_score) / 6, 0.05)

    scores: list[float] = []
    for _ in range(event_count):
        sample = rng.normalvariate(target_average, std_dev)
        sample = clamp(sample, min_score, max_score)
        scores.append(sample)

    if scores:
        current_avg = sum(scores) / len(scores)
        difference = target_average - current_avg
        if abs(difference) > 0.005:
            scores = [clamp(score + difference, min_score, max_score) for score in scores]

    # Nudge a random score towards the extremes to ensure useful coverage.
    if scores:
        min_index = rng.randrange(len(scores))
        max_index = rng.randrange(len(scores))
        scores[min_index] = clamp(scores[min_index] - rng.uniform(0.0, 0.05), min_score, max_score)
        scores[max_index] = clamp(scores[max_index] + rng.uniform(0.0, 0.05), min_score, max_score)

    return scores


def generate_history_records(
    predicted_scores: dict[str, float],
    rng: random.Random,
    min_events: int,
    max_events: int,
    average_offset: float,
    min_score: float,
    max_score: float,
    days_back: int,
    topics: bool,
) -> list[dict[str, object]]:
    """Create the per-subject history records.

    Inputs:
        predicted_scores (Dict[str, float]): Subject names mapped to predicted values.
        rng (random.Random): Random number generator for reproducibility.
        min_events (int): Minimum event count per subject.
        max_events (int): Maximum event count per subject.
        average_offset (float): Average reduction relative to predicted grade.
        min_score (float): Minimum allowed score.
        max_score (float): Maximum allowed score.
        days_back (int): Range for historical event dates.
        topics (bool): Indicates whether predicted grades describe topics, so
            low predicted scores receive additional downward bias.
    Outputs:
        List[Dict[str, object]]: List of dictionaries ready to be written to the database.
    """

    records: list[dict[str, object]] = []
    for subject, predicted_value in predicted_scores.items():
        event_count = rng.randint(min_events, max_events)
        scores = calculate_scores(
            predicted_value,
            event_count,
            average_offset,
            min_score,
            max_score,
            rng,
            topics_mode=topics,
        )
        dates = generate_dates(event_count, rng, days_back)
        for idx in range(event_count):
            record = {
                "subject": subject,
                "type": rng.choice(EVENT_TYPES),
                "score": round(scores[idx], 2),
                "date": dates[idx],
            }
            records.append(record)

    return sorted(records, key=lambda item: item["date"], reverse=True)


def _apply_overrides(database: Path | None, user_id: str | None) -> None:
    """Override configuration for database path and user id when provided."""

    if database:
        config.DATABASE_PATH = Path(database)  # type: ignore[attr-defined]
    if user_id:
        config.DATABASE_USER_ID = str(user_id)  # type: ignore[attr-defined]


def main() -> None:
    """Entry point when executing the module as a script.

    Inputs:
        None directly; configuration is derived from command line arguments.
    Outputs:
        None explicitly; side effects include writing history rows to the database and
        printing the inserted record count for the user's convenience.
    """

    args = parse_args()
    if args.min_events <= 0 or args.max_events <= 0:
        raise ValueError("Minimum and maximum events must be positive integers.")
    if args.min_events > args.max_events:
        raise ValueError("Minimum events cannot exceed maximum events.")
    if args.min_score >= args.max_score:
        raise ValueError("Minimum score must be less than maximum score.")

    _apply_overrides(args.database, args.user_id)

    rng = random.Random(args.seed)
    predicted_scores = io.get_predicted_grades()
    topics_flag = interpret_effective_boolean(args.topics, flag_name="topics")

    records = generate_history_records(
        predicted_scores=predicted_scores,
        rng=rng,
        min_events=args.min_events,
        max_events=args.max_events,
        average_offset=args.average_offset,
        min_score=args.min_score,
        max_score=args.max_score,
        days_back=args.days_back,
        topics=topics_flag,
    )

    inserted = io.append_history_entries(records)
    print(f"Generated {inserted} history entries for user '{config.DATABASE_USER_ID}' into {config.DATABASE_PATH}.")


if __name__ == "__main__":
    main()
