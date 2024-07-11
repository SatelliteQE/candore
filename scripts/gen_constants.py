import csv
import sys

import yaml

KEEP_FIELDS = ["name", "label", "title", "url", "description", "path"]
SKIP_DICT = {}
HELP_TEXT = """
This script processes a comparison report, in the form of a csv file, and outputs a constants file.
This constants file can then be used to run another comparison report with more filtered results.

Usage:
    python gen_constants.py <input_csv_file> [output_yaml_file]

Arguments:
    <input_csv_file>  - The path to the CSV file to be processed.
    [output_yaml_file] - Optional. The path where the resulting YAML file will be saved.
                         If not provided, the output will be saved as 'constants.yaml'.

Example:
    python gen_constants.py my_results.csv my_constants.yaml
"""

csv.field_size_limit(sys.maxsize)


def filter_parts(parts):
    for check in KEEP_FIELDS:
        if check in parts[-1]:
            return True


def add_path_original(path, dest=None):
    if dest is None:
        dest = SKIP_DICT
    curr = path.pop(0)
    if not (c_val := dest.get(curr, {})):
        dest[curr] = c_val
    if len(path) >= 2:
        add_path_original(path, c_val)
    elif path:
        dest[curr].update({path.pop(0): {}})
    else:
        dest[curr] = c_val


def simplify(indict):
    as_list = False
    for key in indict:
        if isinstance(indict[key], dict):
            indict[key] = simplify(indict[key])
        if not indict[key]:
            as_list = True
    if as_list:  # convert the dictionary into a list
        res = []
        for key, val in indict.items():
            if not val:
                res.append(key)
            else:
                res.append({key: val})
        return res
    if len(indict.items()) == 1:
        if not next(iter(indict.values())):
            return next(iter(indict.keys()))
    if any([isinstance(i, str) for i in indict.items()]):
        indict[key] = list(indict[key])
    return indict or {}


if sys.argv[1] in ("-h", "--help", "help"):
    print(HELP_TEXT)
    sys.exit()


input_file = sys.argv[1]
print(f"Getting baseline from {input_file}.")
with open(input_file) as fh:
    reader = csv.reader(fh)
    next(reader)  # pulse for headers
    for row in reader:
        parts = [p for p in row[0].split("/") if not p.isdigit()]
        if not filter_parts(parts):
            add_path_original(parts)

SKIP_DICT = simplify(SKIP_DICT)

if len(sys.argv) > 2:
    as_name = sys.argv[2]
else:
    as_name = "constants.yaml"
with open(as_name, "w") as of:
    export = {"expected_constants": SKIP_DICT, "skipped_constants": []}
    yaml.dump(export, of)

print(f"Constants file saved to {as_name}.")
