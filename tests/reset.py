import json

# Define the path to the JSON file
json_file = "./output/results.json"

# Open and read the JSON file
with open(json_file) as file:
    data = json.load(file)

# Filter out entries with type "Revision" or "Not Studied"
filtered_data = [entry for entry in data if entry["type"] not in ["Revision", "Not Studied"]]

# Write the filtered data back to the JSON file
with open(json_file, "w") as file:
    json.dump(filtered_data, file, indent=4)

print("Entries with type 'Revision' or 'Not Studied' have been removed.")