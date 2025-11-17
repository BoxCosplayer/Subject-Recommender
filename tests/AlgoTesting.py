import json
import math
from datetime import datetime

# Define weights for each type of test
REVISION = 0.1
HOMEWORK_WEIGHT = 0.2
QUIZ_WEIGHT = 0.3
TOPIC_TEST_WEIGHT = 0.4
MOCK_EXAM_WEIGHT = 0.5
EXAM_WEIGHT = 0.6

# Define default and result weights for the overall weighting system
default_weight = 0.7  # Weight for results procured by the system choosing a subject
result_weight = 0.3  # Weight for any past results

# Manually setting default values for each subject
# Default weights represent the confidence of a user in a subject, or predicted grades
gcse_dict = {
    "Maths": 0.5,
    "English Language": 0.6,
    "English Literature": 0.7,
    "Biology": 0.6,
    "Chemistry": 0.7,
    "Physics": 0.5,
    "History": 0.9,
    "Geography": 0.7,
    "Computer Science": 0.4,
    "French": 0.6,
}


def update_system_performance(system_performance):
    # Open and read the JSON file
    with open("input-results.json") as file:
        data = json.load(file)

    # Dictionary to store weighted scores and count of tests for each subject
    subject_scores = {}
    subject_counts = {}

    # Calculate weighted scores based on type of test
    for entry in data:
        subject = entry["subject"]
        grade = entry["score"]
        test_type = entry["type"]

        # Determine weight based on test type
        weight = 1  # Default weight
        match test_type:
            case "Quiz":
                weight = QUIZ_WEIGHT
            case "Topic Test":
                weight = TOPIC_TEST_WEIGHT
            case "Homework":
                weight = HOMEWORK_WEIGHT
            case "Mock Exam":
                weight = MOCK_EXAM_WEIGHT
            case "Exam":
                weight = EXAM_WEIGHT

        # Adjust weight if the score is less / more than a target score
        target_grade = 80

        if grade < target_grade:
            grade_target_difference = target_grade - grade
            x = (1 / 100) * (grade_target_difference**2)
            adjusted_weight = weight * (1 + x / 100)
        elif grade > target_grade:
            grade_target_difference = grade - target_grade
            x = grade_target_difference / 6
            adjusted_weight = weight * (1 + x / 10)
        else:
            adjusted_weight = weight

        # print(adjusted_weight)

        # Apply the adjusted weight to the score
        wGrade = grade * adjusted_weight

        # Accumulate weighted scores and count
        if subject in subject_scores:
            subject_scores[subject] += wGrade
            subject_counts[subject] += weight
        else:
            subject_scores[subject] = wGrade
            subject_counts[subject] = weight

    # Create a new dictionary with weighted average scores
    for subject in system_performance:
        if subject in subject_scores:
            # Calculate the weighted average score
            avg_score = (subject_scores[subject] / subject_counts[subject]) / 100
            wAvg_score = avg_score * result_weight

            wDefault = system_performance[subject] * default_weight
            # Combine with default value using the overall weights
            wAvg = wDefault + wAvg_score
            system_performance[subject] = math.floor(wAvg * 100) / 100

    return system_performance


gcse_dict = update_system_performance(gcse_dict)

# Update and print the system performance
print("System Performance:")
print(gcse_dict, "\n")


# ---------------------- Normalise the scores ----------------------


def normalise(system_performance):
    total_score = sum(system_performance.values())

    # Normalize each score to sum up to 1 while keeping relative differences
    normalised_scores = {subject: score / total_score for subject, score in system_performance.items()}

    # print("normalised_scores:")
    # print(normalised_scores)

    return min(normalised_scores, key=lambda subject: normalised_scores[subject])


no_sessions = 13

# In minutes
session_time = 45
break_time = 15

study_session_record = []
local_gcse_dict = gcse_dict.copy()

for _i in range(no_sessions):
    lowest_subject = normalise(local_gcse_dict)
    # print(lowest_subject)
    study_session_record.append(lowest_subject)

    for subject in local_gcse_dict:
        if subject == lowest_subject:
            local_gcse_dict[subject] += 0.005 * (2.5 * session_time - break_time)
        else:
            local_gcse_dict[subject] -= 0.01


# Shuffle the array
# random.shuffle(study_session_record)

# Print each element on a new line
for subject in study_session_record:
    print(subject)


with open("input-results.json") as file:
    data = json.load(file)

current_date = datetime.now().strftime("%Y-%m-%d")

# Adding entries to the JSON data
for subject in gcse_dict:
    if subject in study_session_record:
        # If studied, add entry with "Revision" type and calculated score
        score = 2 * session_time - break_time
        new_entry = {"subject": subject, "type": "Revision", "score": score, "date": current_date}
    else:
        # If not studied, add entry with negative score based on break time
        score = -1 * break_time
        new_entry = {"subject": subject, "type": "Not Studied", "score": score, "date": current_date}

    # Append the new entry to the data
    data.append(new_entry)

# Write the updated data back to results.json
with open("./output/results.json", "w") as file:
    json.dump(data, file, indent=4)


gcse_dict = update_system_performance(gcse_dict)

# Update and print the system performance\\
print("System Performance:")
print(gcse_dict, "\n")

with open("./output/history.md", "a") as file:
    # Append each subject in study_session_record to the file
    for subject in study_session_record:
        file.write(f"{subject}\n")

print("Study session record has been appended to history.md.")
