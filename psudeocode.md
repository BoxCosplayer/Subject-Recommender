# steps of the program

## pre-processing (utils.py functions)

### inputs

weights as global variables (should be secret)
predicted grades from input file
history of previous grades

### functions

load inputs

for each grade stored in history:
    generate custom weight for that entry
    apply weight to the grade
    store weighted grade
    store original weight of activity

for each subject in history:
    calculate the average score using the values stored [weighted grades and original weights]
    floor values to maintain 2 decimal points

for each subjects score:
    normalise each score by making all the values stored against the subject total to one, whilst maintaining the difference ratio
    output the subject that has the lowest normalised score

## Session generation (very basic)
This is where a lot of forward development will lie

### inputs

Session parameters
    session time
    break time
    number of sessions
history of previous grades

### functions

load inputs

create a local copy of study history of previous grades 

for each session:
    apply pre-processing to local dataset (load, weight & normalise)
    & grab the lowest-scored subject
    add it to the local copy of the history

update history with details of local copy
