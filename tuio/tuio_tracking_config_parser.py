import json
import os
import cv2 as cv
from typing import Dict, List
from core.tuio.tuio_elements import TuioImagePattern, TuioPointer, TuioData
from core.tuio.tuio_tracking_info import TuioTrackingInfo


class TuioTrackingConfigParser(object):
    """
    Parser for JSON formatted tracking config files.

    Example structure of a config file:
    {
        "patterns" :
        [
            {
                "type": "image",
                "data":
                {
                    "tracking_info":
                    {
                        "matching_resource": "matching_image.jpg",
                        "varying_upload_resource": "upload_image.jpg",
                        "fixed_resource_scale": [0.2,0.2]
                        "matching_scale": 0.2
                    }
                }
            },
            {
                "type": "pen",
                "data":
                {
                    "tracking_info":
                    {
                        "matching_resource": "pen_fiducial.jpg",
                    }
                    "rgb": [0,255,0],
                    "radius": 10.0
                }
            }
        ],
        "default_matching_scale": 0.13
    }

    The example above creates two tracking patterns. The first one will create a matching pattern based on
    matching_image.jpg uniformly scale by 0.2. If the pattern is found, upload_image.jpg is uploaded and sent with an
    [x,y] scaling factor of [0.2,0.2]. The second one is a TuioPointer element with a type id of TuioPointer.tu_id_pen.
    To determine the position of the pointer pen_fiducial.jpg will be matched and tracked at a matching scale of 0.13,
    which is determined by the default_matching_scale. The lines drawn by this pen should be colored green, as
    determined by the rgb tag. Additional TuioPointer types are pointer (for a colored dot) and eraser. Any attribute
    added inside the data tag and outside of tracking info will be added to the TuioElement as arbitrary TuioData, using
    the key as mime type and its value as data.

    Note: paths denoted in any image resource fields should reference filepaths relative to the location of the config
    file. This is to support remote tracking scenarios.
    """

    def __init__(self, config_path=""):
        """
        Constructor.

        :param config_path: path to JSON formatted config file.
        """
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
        """
        Setter for JSON formatted config file path. Instance will automatically parse given file.

        :param config_path: filepath to tracking configuration file.

        :return: None
        """
        self._config_path = config_path
        self._resource_dir = os.path.dirname(self._config_path)
        self.parse()

    def get_resource_dir(self):
        """
        Returns the directory where resource files are located.

        :return: str
        """
        return self._resource_dir

    def get_full_resource_path(self, resource_filename):
        """
        Return the joined path of resource dir (location of the config file loaded) and given filename.

        :param resource_filename: name of the file to join with resource dir

        :return: full path str
        """
        return os.path.join(self._resource_dir, resource_filename)

    def get_full_resource_paths(self):
        """
        Return the full paths for all resources loaded from the config file.

        :return: list of filepaths as str
        """
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

    def get_patterns(self) -> Dict[int, TuioImagePattern]:
        """
        Getter to dict of patterns loaded from config file.

        :return: dict
        """
        return self._patterns

    def get_pattern(self, pattern_s_id: int) -> TuioImagePattern:
        """
        Get pattern referenced by given key

        :param pattern_s_id: session id identifying pattern.

        :return: TuioImagePattern
        """
        return self._patterns[pattern_s_id]

    def get_pointers(self) -> Dict[int, TuioPointer]:
        """
        Getter to dict of all pointers loaded from config file.

        :return: dict
        """
        return self._pointers

    def get_pointer(self, pointer_s_id: int) -> TuioPointer:
        """
        Get pointer referenced by given key

        :param pointer_s_id: session id identifying pointer.

        :return: TuioPointer
        """
        return self._pointers[pointer_s_id]

    def get_pattern_tracking_info(self, pattern_s_id: int) -> TuioTrackingInfo:
        """
        Get tracking info extracted for pattern identified by given key.

        :param pattern_s_id: session id identifying pattern.

        :return: TuioTrackingInfo
        """
        return self._pattern_tracking_info[pattern_s_id]

    def get_pointer_tracking_info(self, pointer_s_id: int) -> TuioTrackingInfo:
        """
        Get tracking info extracted for pointer identified by given key.

        :param pointer_s_id: session id identifying pointer.

        :return: TuioTrackingInfo
        """
        return self._pointer_tracking_info[pointer_s_id]

    def get_default_matching_scale(self) -> float:
        """
        Get default matching scale defined in config file.

        :return: float. defaults to 0.0 if nothing defined.
        """
        return self._default_matching_scale

    def has_fixed_resource_scale(self, pattern_s_id: int) -> bool:
        """
        Returns True if a fixed_resource_scale is defined and set for pattern identified by given key. False otherwise.

        :param pattern_s_id: session id identifying pattern.

        :return: bool
        """
        return len(self.get_pattern_tracking_info(pattern_s_id).fixed_resource_scale) == 2

    def get_image_resource_size(self, pattern_s_id: int) -> List[str]:
        """
        Returns [width, height] of image resource identified by pattern. Default resource path is matching_resource of
        tracking_info tag in config. If varying_upload_resource is defined for pattern, respective image extends are
        adjusted.

        :param pattern_s_id: session id identifying pattern.

        :return:
        """
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
        """
        Reads and evaluates data from json formatted config file set on this instance.

        :return: None
        """
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
        """
        Helper function for parse.

        :param elmnt_type: value of the type tag in a pattern dict (see class docs)

        :param elmnt_data: value of the data tag in a pattern dict (see class docs)

        :return: Success of parsing element data
        """
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
        """
        Validates structure of JSON file on a shallow level. required keys currently are 'patterns',
        'default_matching_scale'

        # TODO: extend or remove

        :param json_data: data of json document

        :return: True if wellformed, False otherwise
        """
        required_keys = ["patterns", "default_matching_scale"]
        for rk in required_keys:
            if rk not in json_data:
                return False
        return True

    @staticmethod
    def read_json(config_path):
        """
        Opens will at path and loads json content.

        :param config_path: filepath string

        :return: JSON dict
        """
        file_content = open(config_path).read()
        return json.loads(file_content)
