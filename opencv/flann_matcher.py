import numpy as np
import cv2 as cv


class FlannMatcher(object):
    FLANN_INDEX_KDTREE = 1

    def __init__(self, cv_flann=None):
        self._flann = None
        self._index_params = None
        self._search_params = None
        if cv_flann is not None:
            self._flann = cv_flann
        else:
            self._index_params = dict(algorithm=self.FLANN_INDEX_KDTREE, trees=5)
            self._search_params = dict(checks=50)
            self._flann = cv.FlannBasedMatcher(self._index_params, self._search_params)

    def knn_match(self, pattern, frame):
        """ Returns a list of matched good feature points between pattern and frame.
            Both input parameters are expected to be of type SiftPattern. """
        if pattern.is_empty() or frame.is_empty():
            raise ValueError("pattern and frame cannot be empty.")
        matches = self._flann.knnMatch(
            pattern.get_descriptors(),
            frame.get_descriptors(),
            k=2
        )
        # store all the good matches as per Lowe's ratio test.
        good = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good.append(m)
        return good

    def find_homography(self, pattern, frame, good=None):
        """ Returns the Homography to transform points from pattern, to frame.
            Good is a list of matched points retrieved from knn_match.
            If good is empty, knn_match will be called automatically.
            Returns homography M and mask, as per cv2.findHomography(...). """
        if len(good) == 0:
            good = self.knn_match(pattern, frame)
        if pattern.is_empty() or frame.is_empty():
            raise ValueError("pattern and frame cannot be empty.")
        kp1 = pattern.get_key_points()
        kp2 = frame.get_key_points()
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        return cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)