"""Define tunable parameters and system constants for the subject recommender.

Inputs: None; module-level constants configured inside this file.
Outputs: Named constants consumed across the package for reproducible behaviour.
"""

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
SESSION_TIME_MINUTES = 45
BREAK_TIME_MINUTES = 15
SESSION_COUNT = 6
SHOTS = 7

# TESTING ONLY Data Path Overrides
TEST_PREDICTED_GRADES_PATH = "ALevel_test-predicted.json"
TEST_HISTORY_PATH = "ALevel_test-grades.json"
