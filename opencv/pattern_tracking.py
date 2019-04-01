import numpy as np
import cv2 as cv
import math
import threading

from core.opencv.sift_pattern import SiftPattern
from core.opencv.flann_matcher import FlannMatcher
from core.tuio.tuio_elements import TuioBounds

SIFT = cv.xfeatures2d.SIFT_create()
MIN_MATCH_COUNT = 10
RATIO_TOLERANCE = 0.1


class PatternTrackingThread(threading.Thread):
    """
    Thread performing FLANN based pattern matching (see opencv/flann_matcher.py) task on one image, taking into account
    a list of SIFT patterns (see opencv/sift_pattern.py).
    """

    def __init__(self, image=None, patterns=[]):
        """
        Constructor.

        :param image: opencv image array to use as input for matching task. (set self.image to change later)

        :param patterns: list of SiftPattern instances to match against frame. (see opencv/sift_pattern.py)
        """
        super().__init__()
        self._flann = FlannMatcher()
        self._frame_pattern = SiftPattern(
            "THE-FRAME",
            cv.xfeatures2d.SIFT_create(
                edgeThreshold=12,
                contrastThreshold=0.02,
                sigma=0.8
            )
        )
        self.results = []
        self.image = image
        self.patterns = patterns

    @staticmethod
    def vec_length(v):
        """
        Helper function to calc length of vector.

        :param v: input vector

        :return: length as float
        """
        return math.sqrt(sum([v[i]*v[i] for i in range(0,len(v))]))

    @staticmethod
    def get_rot(M):
        """
        Return the rotation angle of given 2D transformation mat.

        :param M: 2D transformation matrix.

        :return: angle as float.
        """
        rad = -math.atan2(M[0][1], M[0][0])
        deg = math.degrees(rad)
        #print("========")
        #print(rad)
        #print(deg)
        return deg

    @staticmethod
    def get_trans(M):
        """
        Return the translation vector of given 2D transformation mat.

        :param M: 2D transformation matrix

        :return: list [x, y] of translation value
        """
        return [M[0][2], M[1][2]]

    @staticmethod
    def get_scale(M):
        """
        Return the scale vector of given 2D transformation mat.

        :param M: 2D transformation matrix

        :return: list [x, y] of scale value
        """
        s_x = np.sign(M[0][0]) * PatternTrackingThread.vec_length([M[0][0], M[0][1]])
        s_y = np.sign(M[1][1]) * PatternTrackingThread.vec_length([M[1][0], M[1][1]])
        return [s_x, s_y]

    @staticmethod
    def decompose_mat(M):
        """
        Return all affine transformation values for given 2D transformation mat.

        :param M: 2D translation matrix

        :return: {"T": [tx,ty], "R": angle, "S": [sx,sy]}
        """
        return {
            "T": PatternTrackingThread.get_trans(M),
            "R": PatternTrackingThread.get_rot(M),
            "S": PatternTrackingThread.get_scale(M)
        }

    def run(self):
        """
        Thread execution function. Performs FLANN based pattern matching on self.image and list of self.patterns (see
        opencv/sift_pattern.py)

        :return: list of tracking results (see PatternTrackingResult)
        """
        self.results = []
        if self.image is None:
            return
        self._frame_pattern.set_image(self.image)
        h, w, c = self.image.shape
        for pattern in self.patterns:
            good = self._flann.knn_match(pattern, self._frame_pattern)
            if len(good) >= MIN_MATCH_COUNT:
                M, mask = self._flann.find_homography(pattern, self._frame_pattern, good)
                if M is None:
                    continue
                pts = pattern.get_shape_points()
                dst = cv.perspectiveTransform(pts, M)
                rect = cv.minAreaRect(dst)
                # rotation angle of area rect
                # doesn't take into account the pattern orientation
                angle = self.get_rot(M) + 180
                width = max(rect[1][0], rect[1][1])
                height = min(rect[1][0], rect[1][1])
                # validate box
                o_rect = cv.minAreaRect(pts)
                o_width = max(o_rect[1][0], o_rect[1][1])
                o_height = min(o_rect[1][0], o_rect[1][1])
                if o_height == 0 or height == 0:
                    continue
                o_ratio = o_width / o_height
                new_ratio = width / height
                if abs(1 - o_ratio / new_ratio) > RATIO_TOLERANCE:
                    continue
                bnd = TuioBounds(
                    rect[0][0], rect[0][1],  # pos
                    angle,  # rotation
                    width, height  # size
                ).normalized(h, h)
                self.results.append(PatternTrackingResult(pattern.get_id(), bnd))


class PatternTracking(object):
    """
    Offers sequential and concurrent implementation (using PatternTrackingThread) for FLANN based pattern matching (see
    opencv/flann_matcher.py) using SIFT patterns (see opencv/sift_pattern.py).
    """

    def __init__(self):
        """
        Constructor.
        """
        self._flann = FlannMatcher()
        self.patterns = {}
        self._frame_pattern = SiftPattern("THE-FRAME")

    @staticmethod
    def vec_length(v):
        """
        Helper function to calc length of vector.

        :param v: input vector

        :return: length as float
        """
        return math.sqrt(sum([v[i] * v[i] for i in range(0, len(v))]))

    @staticmethod
    def get_rot(M):
        """
        Return the rotation angle of given 2D transformation mat.

        :param M: 2D transformation matrix.

        :return: angle as float.
        """
        rad = -math.atan2(M[0][1], M[0][0])
        deg = math.degrees(rad)
        # print("========")
        # print(rad)
        # print(deg)
        return deg

    @staticmethod
    def get_trans(M):
        """
        Return the translation vector of given 2D transformation mat.

        :param M: 2D transformation matrix

        :return: list [x, y] of translation value
        """
        return [M[0][2], M[1][2]]

    @staticmethod
    def get_scale(M):
        """
        Return the scale vector of given 2D transformation mat.

        :param M: 2D transformation matrix

        :return: list [x, y] of scale value
        """
        s_x = np.sign(M[0][0]) * PatternTracking.vec_length([M[0][0], M[0][1]])
        s_y = np.sign(M[1][1]) * PatternTracking.vec_length([M[1][0], M[1][1]])
        return [s_x, s_y]

    @staticmethod
    def decompose_mat(M):
        """
        Return all affine transformation values for given 2D transformation mat.

        :param M: 2D translation matrix

        :return: {"T": [tx,ty], "R": angle, "S": [sx,sy]}
        """
        return {
            "T": PatternTracking.get_trans(M),
            "R": PatternTracking.get_rot(M),
            "S": PatternTracking.get_scale(M)
        }

    def track(self, image):
        """
        Performs FLANN based pattern matching on self.image and list of self.patterns (see opencv/sift_pattern.py).
        Sequential implementation. Call self.track_concurrent(...) for threaded execution.

        :param image: input image to match against patterns.

        :return: list of tracking results (see PatternTrackingResult)
        """
        res = []
        self._frame_pattern.set_image(image)
        h, w, c = image.shape
        for pattern in self.patterns.values():
            good = self._flann.knn_match(pattern, self._frame_pattern)
            if len(good) >= MIN_MATCH_COUNT:
                M, mask = self._flann.find_homography(pattern, self._frame_pattern, good)
                if M is None:
                    continue
                pts = pattern.get_shape_points()
                dst = cv.perspectiveTransform(pts, M)
                rect = cv.minAreaRect(dst)
                # rotation angle of area rect
                # doesn't take into account the pattern orientation
                angle = self.get_rot(M) + 180
                width = max(rect[1][0], rect[1][1])
                height = min(rect[1][0], rect[1][1])
                # validate box
                o_rect = cv.minAreaRect(pts)
                o_width = max(o_rect[1][0], o_rect[1][1])
                o_height = min(o_rect[1][0], o_rect[1][1])
                if o_height == 0 or height == 0:
                    continue
                o_ratio = o_width / o_height
                new_ratio = width / height
                if abs(1 - o_ratio / new_ratio) > RATIO_TOLERANCE:
                    continue
                bnd = TuioBounds(
                    rect[0][0], rect[0][1],  # pos
                    angle,  # rotation
                    width, height  # size
                ).normalized(h, h)
                res.append(PatternTrackingResult(pattern.get_id(), bnd))
        return res

    def track_concurrent(self, image, num_threads=4):
        """
        Performs FLANN based pattern matching on self.image and list of self.patterns (see opencv/sift_pattern.py).
        Threaded implementation. Call self.track(...) for sequential execution.

        :param image: input image to match against patterns.

        :param num_threads: number of threads to use for tracking work.

        :return: list of tracking results (see PatternTrackingResult)
        """
        threads = []
        patterns = [[] for i in range(0, num_threads)]
        temp = [p for p in self.patterns.values()]
        for i in range(0, len(temp)):
            thread_id = i % num_threads
            patterns[thread_id].append(temp[i])
        for p in patterns:
            if len(p) > 0:
                thread = PatternTrackingThread(image=image, patterns=p)
                thread.patterns = p
                thread.image = image
                thread.start()
                threads.append(thread)
        res = []
        for thread in threads:
            thread.join()
            if len(thread.results) > 0:
                res.extend(thread.results)
        return res

    def load_pattern(self, path, pattern_id=None, matching_scale=1.0):
        """
        Extend self.patterns, by instantiating new SiftPattern based on image data stored at given path.

        :param path: filepath to load image data from.

        :param pattern_id: predefined string to use as pattern id. if None, name of file will be used.

        :param matching_scale: varying scale for pattern size. The smaller the pattern the faster the matching. The
        larger the pattern the higher the precision.

        :return: None
        """
        if pattern_id is None:
            pattern_id = path.split("/")[-1]
        self.patterns[pattern_id] = SiftPattern(pattern_id, SIFT)
        # load and compute descriptors only once
        try:
            self.patterns[pattern_id].load_image(path, matching_scale)
        except cv.error:
            print("FAILURE: could not load image from path", path)

    def load_patterns(self, paths, pattern_ids=[], matching_scale=1.0):
        """
        Extend self.patterns, by instantiating new SiftPatterns based on image data stored at given paths.

        :param paths: list of filepaths to load image data from.

        :param pattern_ids: list of predefined strings to use as pattern_ids. length of list has to be equal to length
        of paths.

        :param matching_scale: varying scale for pattern size. The smaller the pattern the faster the matching. The
        larger the pattern the higher the precision.

        :return: None
        """
        if len(paths) != len(pattern_ids):
            pattern_ids = [None for i in range(0, len(paths))]
        for i in range(0, len(paths)):
            self.load_pattern(paths[i], pattern_ids[i], matching_scale)

    def clear_patterns(self):
        """
        Remove all self.patterns.

        :return: None.
        """
        keys = [k for k in self.patterns.keys()]
        while len(self.patterns) > 0:
            del self.patterns[keys[0]]
            keys.pop(0)


class PatternTrackingResult(object):
    """
    Data Transfer object for FLANN based SIFT pattern matching results. (see PatternTracking & PatternTrackingThread)
    """

    def __init__(self, pattern_id=None, bnd=TuioBounds()):
        """
        Constructor.

        :param pattern_id: string to use as pattern id

        :param bnd: bounding box of matched extends. (see TuioBounds at tuio/tuio_elements.py)
        """
        self.pattern_id = pattern_id
        self.bnd = bnd

    def is_valid(self):
        """
        Returns True if a pattern_id and a non-empty bounding box are set for this instance.

        :return: bool
        """
        return self.pattern_id is not None and not self.bnd.is_empty()
