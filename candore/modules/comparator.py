import json

from candore.modules.variations import Variations, Constants
from candore.utils import last_index_of_element, is_list_contains_dict


class Comparator:
    def __init__(self, settings):
        self.big_key = []
        self.big_diff = {}
        self.big_constant = {}
        self.record_evs = False
        self.variations = Variations(settings)
        self.constants = Constants(settings)
        self.expected_variations = self.variations.expected_variations
        self.skipped_variations = self.variations.skipped_variations
        self.expected_constants = self.constants.expected_constants
        self.skipped_constants = self.constants.skipped_constants



    def remove_verifed_key(self, key):
        reversed_bk = self.big_key[::-1]
        if key in reversed_bk:
            reversed_bk.remove(key)
        self.big_key = reversed_bk[::-1]

    def remove_path(self, identy):
        id_index = last_index_of_element(self.big_key, identy)
        if id_index == -1:
            return
        self.big_key = self.big_key[:id_index]

    def record_variation(self, pre, post, var_details=None):
        big_key = [str(itm) for itm in self.big_key]
        full_path = "/".join(big_key)
        var_full_path = "/".join([itm for itm in self.big_key if not isinstance(itm, int)])
        if var_full_path in self.expected_variations or var_full_path in self.skipped_variations:
            if self.record_evs:
                variation = {
                    "pre": pre,
                    "post": post,
                    "variation": var_details or "Expected(A)",
                }
                self.big_diff.update({full_path: variation})
        elif (
            var_full_path not in self.expected_variations
            and var_full_path not in self.skipped_variations
        ):
            variation = {"pre": pre, "post": post, "variation": var_details or ""}
            self.big_diff.update({full_path: variation})

    def record_constants(self, pre, post, var_details=None):
        big_key = [str(itm) for itm in self.big_key]
        full_path = "/".join(big_key)
        var_full_path = "/".join([itm for itm in self.big_key if not isinstance(itm, int)])
        if var_full_path in self.expected_constants or var_full_path in self.skipped_constants:
            if self.record_evs:
                variation = {
                    "pre": pre,
                    "post": post,
                    "constant": var_details or "Expected(A)",
                }
                self.big_constant.update({full_path: variation})
        elif (
            var_full_path not in self.expected_constants
            and var_full_path not in self.skipped_constants
        ):
            variation = {"pre": pre, "post": post, "constant": var_details or ""}
            self.big_constant.update({full_path: variation})

    def _is_data_type_dict(self, pre, post, unique_key=""):
        if (pre and 'id' in pre) and (post and 'id' in post):
            # Dont compare the entities if the ids are not the same
            if pre['id'] != post['id']:
                return
        for pre_key in pre:
            if pre_key in post:
                key = pre_key
                self.compare_all_pres_with_posts(pre[key], post[key], unique_key=key)
            else:
                self.compare_all_pres_with_posts(
                    pre[pre_key],
                    None,
                    unique_key=pre_key,
                    var_details="Post lookup key missing",
                )
        self.remove_path(unique_key)

    def _is_data_type_list_contains_dict(self, pre, post):
        for pre_entity in pre:
            if not pre_entity:
                continue
            for post_entity in post:
                if not post_entity:
                    continue
                if "id" in pre_entity:
                    if pre_entity["id"] == post_entity["id"]:
                        self.compare_all_pres_with_posts(
                            pre_entity, post_entity, unique_key=pre_entity["id"]
                        )
                else:
                    key = list(pre_entity.keys())[0]
                    if pre_entity[key] == post_entity[key]:
                        self.compare_all_pres_with_posts(
                            pre_entity[key], post_entity[key], unique_key=key
                        )
            if "id" in pre_entity:
                self.remove_path(pre_entity["id"])
            else:
                self.remove_path(pre_entity[list(pre_entity.keys())[0]])

    def _is_data_type_list(self, pre, post, unique_key=""):

        def custom_key(elem):
            return 'None' if elem is None else str(elem)

        if not is_list_contains_dict(pre):
            if sorted(pre, key=custom_key) != sorted(post, key=custom_key):
                self.record_variation(pre, post)
            else:
                self.record_constants(pre, post)
        else:
            self._is_data_type_list_contains_dict(pre, post)
        self.remove_path(unique_key)

    def compare_all_pres_with_posts(self, pre_data, post_data, unique_key="", var_details=None):
        if unique_key:
            self.big_key.append(unique_key)
        if type(pre_data) is dict:
            self._is_data_type_dict(pre_data, post_data, unique_key=unique_key)
        elif type(pre_data) is list:
            self._is_data_type_list(pre_data, post_data, unique_key=unique_key)
        else:
            if pre_data != post_data:
                self.record_variation(pre_data, post_data, var_details)
            else:
                self.record_constants(pre_data, post_data, var_details)
            self.remove_verifed_key(unique_key)

    def compare_json(self, pre_file, post_file, inverse):
        pre_data = post_data = None

        with open(pre_file, "r") as fpre:
            pre_data = json.load(fpre)

        with open(post_file, "r") as fpost:
            post_data = json.load(fpost)

        self.compare_all_pres_with_posts(pre_data, post_data)
        if not inverse:
            return self.big_diff
        else:
            return self.big_constant
