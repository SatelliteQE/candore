import sys

HELP_TEXT = """
This script cleans a CSV file by removing lines that contain consecutive commas (,,,)
and formats the output by aligning the first two columns of each line.

Usage:
    python clean_csv.py <input_file> [output_file]

Arguments:
    <input_file>  - The path to the CSV file to be cleaned.
    [output_file] - Optional. The path where the cleaned CSV file will be saved.
                    If not provided, the output will be saved as 'cleaned.report'.
                    Note: The output report will not be a valid csv file.

Example:
    python clean_csv.py data.csv cleaned_data.report
"""


def strip_extra(line):
    split_line = line.split(",")
    if len(split_line) == 1:
        return line
    return f"{split_line[0]:<50} | {split_line[1]}\n"


def clean_empty(file_handler):
    out_lines = []
    for line in file_handler:
        if ",,," not in line:
            out_lines.append(strip_extra(line))
    return out_lines


if sys.argv[1] in ("-h", "--help", "help"):
    print(HELP_TEXT)
    sys.exit()

to_clean = sys.argv[1]
with open(to_clean) as fh:
    cleaned = clean_empty(fh)

if len(sys.argv) > 2:
    as_name = sys.argv[2]
else:
    as_name = "cleaned.report"
with open(as_name, "w") as fh:
    fh.writelines(cleaned)

print(f"Cleaned file saved to {as_name}")
