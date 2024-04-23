"""
An utility helpers module
"""
from pathlib import Path
import yaml


def last_index_of_element(arr, element):
    for i in range(len(arr) - 1, -1, -1):
        if arr[i] == element:
            return i
    return -1


def is_list_contains_dict(_list):
    contains_dict = any(isinstance(element, dict) for element in _list)
    return contains_dict


def yaml_reader(file_path=None):
    templates_path = Path(file_path)
    if not templates_path.exists():
        print(f"The file {templates_path} does not exist.")
    with templates_path.open() as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)
    return yaml_data


def get_yaml_paths(yaml_data, prefix="", separator="/"):
    paths = []
    if isinstance(yaml_data, dict):
        for key, value in yaml_data.items():
            paths.extend(get_yaml_paths(value, f"{prefix}{key}{separator}"))
    elif isinstance(yaml_data, list):
        for item in yaml_data:
            paths.extend(get_yaml_paths(item, prefix, separator))
    else:
        paths.append(f"{prefix}{yaml_data}")
    return paths