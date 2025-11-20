"""Script that generates synthetic grade history entries from predicted grades.

This module reads a JSON file containing predicted subject performance values
(floats between 0 and 1) and writes a new JSON file following the same event
format as ``gcse_test-grades.json``. Inputs are provided through the command
line: an input predicted grade file path and an optional output file path. The
resulting JSON file is written to disk and contains objects with ``subject``,
``type``, ``score`` (0.3-1.0), and ``date`` keys.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import random
from collections.abc import Iterable, Sequence

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
        argparse.Namespace: Parsed arguments including file paths, generation
            parameters, and random seed options.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Generate a grade history JSON file from a predicted grades JSON "
            "file. Scores are scaled between the requested minimum and maximum "
            "values, defaulting to 0.3-1.0."
        )
    )
    parser.add_argument(
        "predicted_file",
        type=pathlib.Path,
        help="Path to the JSON file containing predicted grades.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        help=(
            "Optional output file path. When omitted, '-predicted' in the input filename is replaced with '-grades'."
        ),
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
        flag_name (str): Friendly name used to clarify potential error
            messages.
    Outputs:
        bool: True when the value represents an affirmative option, otherwise
            False.
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


def load_predicted_scores(predicted_path: pathlib.Path) -> dict[str, float]:
    """Load the predicted scores from a JSON file into a subject mapping.

    Inputs:
        predicted_path (pathlib.Path): Location of the JSON file that stores
            predicted grades either as a mapping or a list containing mappings.
    Outputs:
        Dict[str, float]: Dictionary where keys are subject names and values
            are predicted performance values scaled 0-1.
    """

    with predicted_path.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)

    if isinstance(raw_data, dict):
        dataset: Iterable[dict[str, float]] = (raw_data,)
    elif isinstance(raw_data, list):
        dataset = raw_data
    else:
        raise ValueError("Predicted grades file must contain a dictionary or a list of dictionaries.")

    merged: dict[str, float] = {}
    for entry in dataset:
        if not isinstance(entry, dict):
            raise ValueError("Each predicted grade entry must be a JSON object.")
        for subject, value in entry.items():
            try:
                score = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Predicted score for '{subject}' must be numeric.") from exc
            merged[subject] = score

    if not merged:
        raise ValueError("No predicted scores found in the supplied file.")

    return merged


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
        predicted_scores (Dict[str, float]): Subject names mapped to predicted
            values.
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
        List[Dict[str, object]]: List of dictionaries ready to be dumped to
            JSON following the required format.
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


def determine_output_path(predicted_path: pathlib.Path, explicit: pathlib.Path | None) -> pathlib.Path:
    """Determine the output file path based on an optional override.

    Inputs:
        predicted_path (pathlib.Path): Input predicted grades path.
        explicit (pathlib.Path | None): User supplied output path, if any.
    Outputs:
        pathlib.Path: File path where the generated history JSON should be written.
    """

    if explicit:
        return explicit

    replaced_name = predicted_path.name.replace("-predicted", "-grades")
    if replaced_name == predicted_path.name:
        replaced_name = predicted_path.stem + "-grades.json"
    return predicted_path.with_name(replaced_name)


def write_history(records: Sequence[dict[str, object]], output_path: pathlib.Path) -> None:
    """Persist the generated history records to disk.

    Inputs:
        records (Sequence[Dict[str, object]]): List of event dictionaries to write.
        output_path (pathlib.Path): File path for the resulting JSON file.
    Outputs:
        None directly; the function creates or overwrites output_path on disk.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=4)


def main() -> None:
    """Entry point when executing the module as a script.

    Inputs:
        None directly; configuration is derived from command line arguments.
    Outputs:
        None explicitly; side effects include writing the target JSON file and
            printing the destination path for the user's convenience.
    """

    args = parse_args()
    if args.min_events <= 0 or args.max_events <= 0:
        raise ValueError("Minimum and maximum events must be positive integers.")
    if args.min_events > args.max_events:
        raise ValueError("Minimum events cannot exceed maximum events.")
    if args.min_score >= args.max_score:
        raise ValueError("Minimum score must be less than maximum score.")

    rng = random.Random(args.seed)
    predicted_scores = load_predicted_scores(args.predicted_file)
    output_path = determine_output_path(args.predicted_file, args.output)
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

    write_history(records, output_path)
    print(f"Generated history written to {output_path}")


if __name__ == "__main__":
    main()
