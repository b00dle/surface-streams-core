import cv2 as cv
from core import gstreamer


class CvUdpVideoReceiver(object):
    """
    Implements a Gst based cv2.VideoCapture to receive video frames over udp, decode them, and return data on demand.

    Can handle multiple stream encodings (jpeg, vp8, vp9, mp4, h264, h265).

    (example) gst pipeline description created for 'jpeg':
    gst-launch-1.0 udpsrc port=5000 ! application/x-rtp, media=application ! queue !
        rtpgstdepay ! jpegdec ! videoconvert ! gtksink
    """

    def __init__(self, port, protocol="jpeg", width=-1):
        """
        Constructor.

        :param port: Port to receive input frames at.

        :param protocol: Protocol encoding of the input stream. Choose jpeg, vp8, vp9, mp4, h264 or h265.

        :param width: alternate videoscale of the input stream. (-1 means, determined automatically)
        """
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
        """
        Release cv2.VideoCapture(...). Call prior to destructing instance, to ensure all refs are cleared.

        :return: None
        """
        self._capture.release()

    def capture(self):
        """
        Returns the most recent frame or None if nothing is being captured.

        Output can be visualized using cv2.imshow(self.capture()).

        :return: frame data as opencv image array.
        """
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
        """
        Get the internal capturing state of cv2.VideoCapture(...) device used.

        :return: bool
        """
        return not self._capture_finished

