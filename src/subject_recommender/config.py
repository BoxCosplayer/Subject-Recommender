"""Central location for tunable parameters and system constants."""

from __future__ import annotations

# FIXED Assessment weights
REVISION_WEIGHT = 0.1
HOMEWORK_WEIGHT = 0.2
QUIZ_WEIGHT = 0.3
TOPIC_TEST_WEIGHT = 0.4
MOCK_EXAM_WEIGHT = 0.5
EXAM_WEIGHT = 0.6

# FIXED System weighting factors
# update to factor date as a function
RECENT_WEIGHT = 0.7
HISTORY_WEIGHT = 0.3


# TUNABLE Session Parameters
SESSION_COUNT = 6
SESSION_TIME_MINUTES = 45
BREAK_TIME_MINUTES = 15
SPINS = 10