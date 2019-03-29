import numpy as np
import cv2 as cv
import time
import math
import threading

from scipy.spatial import distance as dist
from opencv.sift_pattern import SiftPattern
from opencv.flann_matcher import FlannMatcher
from tuio.tuio_elements import TuioBounds

SIFT = cv.xfeatures2d.SIFT_create()
MIN_MATCH_COUNT = 10
RATIO_TOLERANCE = 0.1


def order_points(pts):
    # sort the points based on their x-coordinates
    xSorted = pts[np.argsort(pts[:, 0]), :]

    # grab the left-most and right-most points from the sorted
    # x-roodinate points
    leftMost = xSorted[:2, :]
    rightMost = xSorted[2:, :]

    # now, sort the left-most coordinates according to their
    # y-coordinates so we can grab the top-left and bottom-left
    # points, respectively
    leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
    (tl, bl) = leftMost

    # now that we have the top-left coordinate, use it as an
    # anchor to calculate the Euclidean distance between the
    # top-left and right-most points; by the Pythagorean
    # theorem, the point with the largest distance will be
    # our bottom-right point
    D = dist.cdist(tl[np.newaxis], rightMost, "euclidean")[0]
    (br, tr) = rightMost[np.argsort(D)[::-1], :]

    # return the coordinates in top-left, top-right,
    # bottom-right, and bottom-left order
    return np.array([tr, tl, bl, br], dtype="float32")


class PatternTrackingThread(threading.Thread):
    def __init__(self, image=None, patterns=[]):
        super().__init__()
        self._flann = FlannMatcher()
        self._frame_pattern = SiftPattern(
            "THE-FRAME",
            cv.xfeatures2d.SIFT_create(
                #nfeatures=2000,
                edgeThreshold=12,
                contrastThreshold=0.02,
                sigma=0.8
            )
        )
        self.results = []
        self.image = image
        self.patterns = patterns

    def vec_length(self, v):
        return math.sqrt(sum([v[i]*v[i] for i in range(0,len(v))]))

    def get_rot(self, M):
        rad = -math.atan2(M[0][1], M[0][0])
        deg = math.degrees(rad)
        #print("========")
        #print(rad)
        #print(deg)
        return deg

    def get_trans(self, M):
        return [M[0][2], M[1][2]]

    def get_scale(self, M):
        s_x = np.sign(M[0][0]) * self.vec_length([M[0][0], M[0][1]])
        s_y = np.sign(M[1][1]) * self.vec_length([M[1][0], M[1][1]])
        return [s_x, s_y]

    def decompose_mat(self, M):
        return {"T": self.get_trans(M), "R": self.get_rot(M), "S": self.get_scale(M)}

    def run(self):
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
    def __init__(self):
        self._flann = FlannMatcher()
        self.patterns = {}
        self._frame_pattern = SiftPattern("THE-FRAME")

    def vec_length(self, v):
        return math.sqrt(sum([v[i]*v[i] for i in range(0,len(v))]))

    def get_rot(self, M):
        rad = -math.atan2(M[0][1], M[0][0])
        deg = math.degrees(rad)
        return deg

    def get_trans(self, M):
        return [M[0][2], M[1][2]]

    def get_scale(self, M):
        s_x = np.sign(M[0][0]) * self.vec_length([M[0][0], M[0][1]])
        s_y = np.sign(M[1][1]) * self.vec_length([M[1][0], M[1][1]])
        return [s_x, s_y]

    def decompose_mat(self, M):
        return {"T": self.get_trans(M), "R": self.get_rot(M), "S": self.get_scale(M)}

    def track(self, image):
        """ SIFT/FLANN based object recognition is performed on image.
            frame should be a cv image. Matched patterns can be managed
            using patterns variable of this instance.
            if overlay_result is True then a frame will be drawn
            around objects found. Returns a list of CvTrackingResults. """
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
        if pattern_id is None:
            pattern_id = path.split("/")[-1]
        self.patterns[pattern_id] = SiftPattern(pattern_id, SIFT)
        # load and compute descriptors only once
        try:
            self.patterns[pattern_id].load_image(path, matching_scale)
        except cv.error:
            print("FAILURE: could not load image from path", path)

    def load_patterns(self, paths, pattern_ids=[], matching_scale=1.0):
        if len(paths) != len(pattern_ids):
            pattern_ids = [None for i in range(0, len(paths))]
        for i in range(0, len(paths)):
            self.load_pattern(paths[i], pattern_ids[i], matching_scale)

    def clear_patterns(self):
        keys = [k for k in self.patterns.keys()]
        while len(self.patterns) > 0:
            del self.patterns[keys[0]]
            keys.pop(0)


class PatternTrackingResult(object):
    """ Data Transfer object for Tracking Results. """

    def __init__(self, pattern_id=None, bnd=TuioBounds()):
        self.pattern_id = pattern_id
        self.bnd = bnd

    def is_valid(self):
        return self.pattern_id is not None and not self.bnd.is_empty()


def run(pattern_paths, video_path):
    tracker = PatternTracking()
    tracker.load_patterns(pattern_paths)

    # setup video capture
    cap = cv.VideoCapture(
        "filesrc location=\"" + video_path + "\" ! decodebin ! videoconvert ! "
                                             "videoscale ! video/x-raw, width=480, pixel-aspect-ratio=1/1 ! appsink"
    )

    if not cap.isOpened():
        print("Cannot capture test src. Exiting.")
        quit()

    since_print = 0.0
    fps_collection = []
    track_num = 0
    while True:
        start_time = time.time()

        ret, frame = cap.read()
        if ret == False:
            break

        h, w, c = frame.shape

        i = 0
        for res in tracker.track(frame):
            bnd_s = res.bnd.scaled(h, h)
            box = cv.boxPoints((
               (bnd_s.x_pos, bnd_s.y_pos),
               (bnd_s.width, bnd_s.height),
               bnd_s.angle
            ))
            frame = cv.polylines(frame, [np.int32(box)], True, 255, 3, cv.LINE_AA)
            if i == track_num:
                img = tracker.patterns[res.pattern_id].get_image().copy()
                img_h, img_w = img.shape
                pts = np.float32([[0, 0], [0, img_h - 1], [img_w - 1, img_h - 1], [img_w - 1, 0]]).reshape(-1, 1, 2)
                M = cv.getPerspectiveTransform(pts, order_points(box))
                img = cv.warpPerspective(img, M, (w, h))
                cv.imshow("tracked-pattern", img)
            i += 1

        cv.imshow("CVtest", frame)

        elapsed_time = time.time()-start_time
        fps_collection.append(1.0/elapsed_time)
        since_print += elapsed_time
        if since_print > 1.0:
            print("avg fps:", int(sum(fps_collection)/float(len(fps_collection))))
            fps_collection = []
            since_print = 0.0

        key_pressed = cv.waitKey(1) & 0xFF
        if key_pressed == ord('q'):
            break
        elif key_pressed == ord('w'):
            track_num = (track_num + 1) % len(tracker.patterns)