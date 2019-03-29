import numpy as np
import cv2 as cv


class SiftPattern(object):
    def __init__(self, pattern_id, cv_sift=None):
        self._id = pattern_id
        self._img = None
        self._key_points = None
        self._descriptors = None
        self._sift = cv_sift

    def get_id(self):
        return self._id

    def get_image(self):
        return self._img

    def get_key_points(self):
        return self._key_points

    def get_descriptors(self):
        return self._descriptors

    def get_shape(self):
        if self.is_empty():
            return None
        return self._img.shape

    def get_shape_points(self):
        if self.is_empty():
            return None
        h, w = self._img.shape
        return np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)

    def load_image(self, file_path, scale=1.0):
        self._img = cv.imread(file_path, 0)
        if scale != 1:
            self._img = cv.resize(self._img, (0,0), fx=scale, fy=scale)
        self._detect_and_compute()

    def set_image(self, img):
        self._img = img
        self._detect_and_compute()

    def is_empty(self):
        return self._img is None

    def _detect_and_compute(self):
        if self.is_empty():
            return
        if self._sift is None:
            self._sift = cv.xfeatures2d.SIFT_create(sigma=2.0)
        self._key_points, self._descriptors = self._sift.detectAndCompute(self._img, None)