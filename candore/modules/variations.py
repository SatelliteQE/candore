"""
A module responsible for calculating expected and skipped variations from
`conf/variations` yaml file and convert them into processable list
"""
from functools import cached_property
from candore.utils import yaml_reader, get_yaml_paths


class Variations:
    def __init__(self, settings):
        self.settings = settings

    @cached_property
    def variations(self):
        yaml_data = yaml_reader(file_path=getattr(self.settings.candore, "var_file", None))
        return yaml_data

    @cached_property
    def expected_variations(self):
        yaml_data = self.variations.get("expected_variations") if self.variations else None
        return get_yaml_paths(yaml_data=yaml_data)


    @cached_property
    def skipped_variations(self):
        yaml_data = self.variations.get("skipped_variations") if self.variations else None
        return get_yaml_paths(yaml_data=yaml_data)


class Constants:
    def __init__(self, settings):
        self.settings = settings

    @cached_property
    def constants(self):
        yaml_data = yaml_reader(file_path=getattr(self.settings.candore, "constant_file", None))
        return yaml_data

    @cached_property
    def expected_constants(self):
        yaml_data = self.constants.get("expected_constants") if self.constants else None
        return get_yaml_paths(yaml_data=yaml_data)

    @cached_property
    def skipped_constants(self):
        yaml_data = self.constants.get("skipped_constants") if self.constants else None
        return get_yaml_paths(yaml_data=yaml_data)
