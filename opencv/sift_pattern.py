import numpy as np
import cv2 as cv


class SiftPattern(object):
    """
    Wrapper class for convenient access of opencv sift patterns (see cv2.xfeatures2d.SIFT_create(...)).
    Requires non-free modules of python cv2 module to being built.
    """

    def __init__(self, pattern_id, cv_sift=None):
        """
        Constructor.

        :param pattern_id: string to use for pattern identification.

        :param cv_sift: externally defined cv2.xfeatures2d.SIFT_create(...) return object. If None, an instance will be
        automatically created.
        """
        self._id = pattern_id
        self._img = None
        self._key_points = None
        self._descriptors = None
        self._sift = cv_sift

    def get_id(self):
        """
        Getter for user id of this pattern.

        :return: user_id as used in TuioImagePattern (see tuio/tuio_elements.py)
        """
        return self._id

    def get_image(self):
        """
        Getter for image resource tied to this instance.

        :return: opencv image array.
        """
        return self._img

    def get_key_points(self):
        """
        Getter for computed key points of pattern.

        :return: list of key points (see self._detect_and_compute())
        """
        return self._key_points

    def get_descriptors(self):
        """
        Getter for computed descriptors of pattern.

        :return: list of descriptors (see self._detect_and_compute())
        """
        return self._descriptors

    def get_shape(self):
        """
        Getter for shape of image resource.

        :return: h, w, c data of self._img.shape
        """
        if self.is_empty():
            return None
        return self._img.shape

    def get_shape_points(self):
        """
        Getter for corner points of image shape.

        :return: np array of corner points.
        """
        if self.is_empty():
            return None
        h, w = self._img.shape
        return np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)

    def load_image(self, file_path, scale=1.0):
        """
        Loads pattern data from file. Will detect and compute key points and descriptors.

        :param file_path: filepath of image resource for pattern

        :param scale: scale to apply prior to detecting key points and descriptors. smaller sizes increase computational
        time, but decrease matching performance.

        :return: None
        """
        self._img = cv.imread(file_path, 0)
        if scale != 1:
            self._img = cv.resize(self._img, (0,0), fx=scale, fy=scale)
        self._detect_and_compute()

    def set_image(self, img):
        """
        Set image resource data for this pattern. Will detect and compute key points and descriptors.

        :param img: image resource data.

        :return: None
        """
        self._img = img
        self._detect_and_compute()

    def is_empty(self):
        """
        Returns True if no resource data has been set for this pattern.

        :return: bool
        """
        return self._img is None

    def _detect_and_compute(self):
        """
        compute key points and descriptors as per:

        sift = cv2.xfeatures2d.SIFT_create(...)

        kp, descr = sift.detectAndCompute(...)

        :return: None
        """
        if self.is_empty():
            return
        if self._sift is None:
            self._sift = cv.xfeatures2d.SIFT_create(sigma=2.0)
        self._key_points, self._descriptors = self._sift.detectAndCompute(self._img, None)