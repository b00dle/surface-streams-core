import json
import os
import cv2 as cv
from typing import Dict, List
from tuio.tuio_elements import TuioImagePattern, TuioPointer, TuioData
from tuio.tuio_tracking_info import TuioTrackingInfo


class TuioTrackingConfigParser(object):
    def __init__(self, config_path=""):
        self._patterns = {}
        self._pattern_tracking_info = {}
        self._pointers = {}
        self._pointer_tracking_info = {}
        self._image_resource_sizes = {}
        self._default_matching_scale = 0.0
        self._config_path = config_path
        self._resource_dir = os.path.dirname(self._config_path)
        self.parse()

    def set_config_path(self, config_path):
        self._config_path = config_path
        self._resource_dir = os.path.dirname(self._config_path)
        self.parse()

    def get_resource_dir(self):
        return self._resource_dir

    def get_full_resource_path(self, resource_filename):
        return os.path.join(self._resource_dir, resource_filename)

    def get_full_resource_paths(self):
        res = []
        for pattern in self._patterns.values():
            info = self.get_pattern_tracking_info(pattern.get_s_id())
            res.append(self.get_full_resource_path(info.matching_resource))
            if len(info.varying_upload_resource) > 0:
                res.append(self.get_full_resource_path(info.varying_upload_resource))
        for pointer in self._pointers.values():
            info = self.get_pointer_tracking_info(pointer.s_id)
            res.append(self.get_full_resource_path(info.matching_resource))
        return res

    def get_patterns(self) -> Dict[str, TuioImagePattern]:
        return self._patterns

    def get_pattern(self, pattern_s_id: int) -> TuioImagePattern:
        return self._patterns[pattern_s_id]

    def get_pointers(self) -> Dict[str, TuioPointer]:
        return self._pointers

    def get_pointer(self, pointer_s_id: int) -> TuioPointer:
        return self._pointers[pointer_s_id]

    def get_pattern_tracking_info(self, pattern_s_id: int) -> TuioTrackingInfo:
        return self._pattern_tracking_info[pattern_s_id]

    def get_pointer_tracking_info(self, pattern_s_id: int) -> TuioTrackingInfo:
        return self._pointer_tracking_info[pattern_s_id]

    def get_default_matching_scale(self) -> float:
        return self._default_matching_scale

    def has_fixed_resource_scale(self, pattern_s_id: int) -> bool:
        return len(self.get_pattern_tracking_info(pattern_s_id).fixed_resource_scale) == 2

    def get_image_resource_size(self, pattern_s_id: int) -> List[int]:
        if pattern_s_id in self._image_resource_sizes:
            return self._image_resource_sizes[pattern_s_id]
        elif pattern_s_id not in self._patterns:
            raise ValueError("Given session_id does not reference an image pattern")
        tracking_info = self.get_pattern_tracking_info(pattern_s_id)
        resource = tracking_info.matching_resource
        if len(tracking_info.varying_upload_resource) > 0:
            resource = tracking_info.varying_upload_resource
        img = cv.imread(resource, 0)
        h, w = img.shape
        res = [w, h]
        if len(tracking_info.fixed_resource_scale) == 2:
            res[0] *= tracking_info.fixed_resource_scale[0]
            res[1] *= tracking_info.fixed_resource_scale[1]
        self._image_resource_sizes[pattern_s_id] = res
        return res

    def parse(self):
        """ Reads data from json formatted config file. """
        self._patterns = {}
        self._pattern_tracking_info = {}
        self._pointers = {}
        self._pointer_tracking_info = {}
        self._image_resource_sizes = {}
        self._default_matching_scale = 0.0
        if len(self._config_path) == 0:
            return

        if not os.path.isfile(self._config_path):
            raise ValueError("FAILURE: cannot read tuio config.\n  > specified path '"+self._config_path+"' is no file.")

        json_data = self.read_json(self._config_path)
        if not self.validate_root_structure(json_data):
            return

        for elmt_desc in json_data["patterns"]:
            if "type" not in elmt_desc or "data" not in elmt_desc:
                print("FAILURE: wrong format for pattern description.")
                print("  > parser expects definition for 'type' and 'data'")
                print("  > got", elmt_desc)
                print("  > skipping.")
                continue
            if not self._parse_add_element(elmt_desc["type"], elmt_desc["data"]):
                print("FAILURE: couldn't add element")
                print("  > type", elmt_desc["type"])
                print("  > data", elmt_desc["data"])

        self._default_matching_scale = float(json_data["default_matching_scale"])

    def _parse_add_element(self, elmnt_type, elmnt_data):
        info = None
        if "tracking_info" in elmnt_data:
            info = TuioTrackingInfo(**elmnt_data["tracking_info"])
        else:
            return False

        captured_data = ["tracking_info"]
        if elmnt_type == "image":
            elmt = TuioImagePattern()
            self._patterns[elmt.get_s_id()] = elmt
            self._pattern_tracking_info[elmt.get_s_id()] = info
        elif elmnt_type == "pen":
            elmt = TuioPointer(tu_id=TuioPointer.tu_id_pen)
            if "radius" in elmnt_data:
                elmt.radius = float(elmnt_data["radius"])
                captured_data.append("radius")
            self._pointers[elmt.s_id] = elmt
            self._pointer_tracking_info[elmt.s_id] = info
        elif elmnt_type == "pointer":
            elmt = TuioPointer(tu_id=TuioPointer.tu_id_pointer)
            if "radius" in elmnt_data:
                elmt.radius = float(elmnt_data["radius"])
                captured_data.append("radius")
            self._pointers[elmt.s_id] = elmt
            self._pointer_tracking_info[elmt.s_id] = info
        elif elmnt_type == "eraser":
            elmt = TuioPointer(tu_id=TuioPointer.tu_id_eraser)
            if "radius" in elmnt_data:
                elmt.radius = float(elmnt_data["radius"])
                captured_data.append("radius")
            self._pointers[elmt.s_id] = elmt
            self._pointer_tracking_info[elmt.s_id] = info
        else:
            return False

        misc_data = [
            TuioData(mime_type=mime_type, data=data)
            for mime_type, data in elmnt_data.items()
            if mime_type not in captured_data
        ]

        elmt.append_data_list(misc_data)

        return True

    @staticmethod
    def validate_root_structure(json_data):
        required_keys = ["patterns", "default_matching_scale"]
        for rk in required_keys:
            if rk not in json_data:
                return False
        return True

    @staticmethod
    def read_json(config_path):
        file_content = open(config_path).read()
        return json.loads(file_content)