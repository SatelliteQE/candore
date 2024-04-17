"""
An utility helpers module
"""


def last_index_of_element(arr, element):
    for i in range(len(arr) - 1, -1, -1):
        if arr[i] == element:
            return i
    return -1


def is_list_contains_dict(_list):
    contains_dict = any(isinstance(element, dict) for element in _list)
    return contains_dict
