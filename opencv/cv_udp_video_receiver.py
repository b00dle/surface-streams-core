import cv2 as cv
import gstreamer


class CvUdpVideoReceiver(object):
    def __init__(self, port, protocol="jpeg", width=-1):
        self._protocol = protocol
        self._port = port
        self._capture = None
        self._pipeline_description = ""
        self._capture_finished = False
        self._width = width
        self._init_capture()

    def _init_capture(self):
        self._pipeline_description = "udpsrc port="+str(self._port) + " ! "

        if self._protocol == "jpeg":
            self._pipeline_description += gstreamer.JPEG_CAPS + " ! queue ! "
            self._pipeline_description += "rtpgstdepay ! "
            self._pipeline_description += "jpegdec ! "
        elif self._protocol == "vp8":
            self._pipeline_description += gstreamer.VP8_CAPS + " ! queue ! "
            self._pipeline_description += "rtpvp8depay ! "
            self._pipeline_description += "vp8dec ! "
        elif self._protocol == "vp9":
            self._pipeline_description += gstreamer.VP9_CAPS + " ! queue ! "
            self._pipeline_description += "rtpvp9depay ! "
            self._pipeline_description += "vp9dec ! "
        elif self._protocol == "mp4":
            self._pipeline_description += gstreamer.MP4_CAPS + " ! queue ! "
            self._pipeline_description += "rtpmp4vdepay ! "
            self._pipeline_description += "avdec_mpeg4 ! "
        elif self._protocol == "h264":
            self._pipeline_description += gstreamer.H264_CAPS + " ! queue ! "
            self._pipeline_description += "rtph264depay ! "
            self._pipeline_description += "avdec_h264 ! "
        elif self._protocol == "h265":
            self._pipeline_description += gstreamer.H265_CAPS + " ! queue ! "
            self._pipeline_description += "rtph265depay ! "
            self._pipeline_description += "avdec_h264 ! "

        if self._width > 0:
            self._pipeline_description += "videoconvert ! videoscale ! video/x-raw, width=" + str(self._width) + \
                ", pixel-aspect-ratio=1/1 ! appsink sync=false"
        else:
            self._pipeline_description += "videoconvert ! appsink sync=false"
        self._capture = cv.VideoCapture(self._pipeline_description)

    def release(self):
        self._capture.release()

    def capture(self):
        """ returns the currently captured frame or None if not capturing. """
        if not self._capture.isOpened():
            print("CvVideoReceiver\n  > Cannot capture from description")
            print(self._pipeline_description)
            return None

        if self._capture_finished:
            print("CvVideoReceiver\n  > capture finished.")
            return None

        ret, frame = self._capture.read()

        if ret == False:
            self._capture_finished = True
            return None

        return frame

    def is_capturing(self):
        return not self._capture_finished

