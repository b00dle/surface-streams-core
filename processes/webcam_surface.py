from core.processes import ProcessWrapper


class WebcamSurface(ProcessWrapper):
    """
    Class used to encapsulate execution of Surface Streams streaming process. Raw Data captured from a webcam is send
    over udp using Gstreamer. This class can be used as an input process of a client in the Surface Streams 2.0
    architecture.

    A pipeline of the following form will be constructed (example):

    v4l2src device=/dev/video1 ! jpegenc ! rtpgstpay ! udpsink port=9999

    (check out https://github.com/b00dle/surface-streams-client for full Surface Streams 2.0 client usage scenario.)
    """
    def __init__(self, server_port, my_port, server_ip="0.0.0.0", my_ip="0.0.0.0", protocol="jpeg",
                 device="/dev/video0", server_stream_width=320, monitor=True,
                 input_adjustment={}):#input_adjustment={"saturation":2.0, "brightness":0.0}):
        """
        Constructor

        :param server_port: udpsink (GstElement) port. In a Surface Streams 2.0 setup this should be where the server
        expects frame input from the client.

        :param my_port: secondary udpsink (GstElement) port. In a Surface Streams 2.0 setup this should be where the
        pattern matching process expects input.

        :param server_ip: ip of the server to send output to.

        :param my_ip: secondary udpsink (GstElement) ip. In a Surface Streams 2.0 setup this should be the ip address of
        the pattern matching process. For local tracking scenarios choose 0.0.0.0, else choose remote machine ip.

        :param protocol: frame protocol encoding. Choose 'jpeg', 'vp8', 'vp9', 'mp4', 'h264' or 'h265'

        :param device: device identifier (to list available devices call: v4l2-ctl --list-devices)

        :param server_stream_width: width of the frame sent to server_ip:server_port

        :param monitor: if True an fpsdisplaysink (GstElement) will produce additional output of the pipeline produced
        by the executable.

        :param input_adjustment: image processing applied to the raw camera stream. Call 'gst-inspect-1.0 videobalance'
        to check available key value pairs. example dict format: {"brightness":0.5, "saturation":1.5}
        """
        super().__init__()
        self._server_ip = server_ip
        self._server_port = server_port
        self._server_stream_width = server_stream_width
        self._my_port = my_port
        self._my_ip = my_ip
        self._protocol = protocol
        self._monitor = monitor
        self._pipeline_description = ""
        self._device = device
        self._input_adjustment = input_adjustment
        self._compute_launch_command()

    def _compute_launch_command(self):
        """
        BC override.
        """
        gst_videoscale_server = "videoscale ! " \
                         "video/x-raw, width=" + str(self._server_stream_width) + ", " \
                         "pixel-aspect-ratio=1/1"
        gst_videoscale_tracker = "videoscale ! " \
                                "video/x-raw, width=" + str(640) + ", pixel-aspect-ratio=1/1"

        gst_encoding = ""
        if self._protocol == "jpeg":
            gst_encoding += "jpegenc ! rtpgstpay"
        elif self._protocol == "vp8":
            gst_encoding += "vp8enc ! rtpvp8pay"
        elif self._protocol == "vp9":
            gst_encoding += "vp9enc ! rtpvp9pay"
        elif self._protocol == "mp4":
            gst_encoding += "avenc_mpeg4 ! rtpmp4vpay"
        elif self._protocol == "h264":
            gst_encoding += "avenc_h264 ! rtph264pay"
        elif self._protocol == "h265":
            gst_encoding += "avenc_h264 ! rtph265pay"

        self._pipeline_description += "v4l2src device="+str(self._device)+" ! decodebin ! videoconvert ! "
        if len(self._input_adjustment) > 0:
            self._pipeline_description += "videobalance "
            for key, value in self._input_adjustment.items():
                self._pipeline_description += str(key) + "=" + str(value) + " "
            self._pipeline_description += "! "
        self._pipeline_description += "aspectratiocrop aspect-ratio=16/9 ! videoflip method=rotate-180 ! "
        self._pipeline_description += "tee name=t ! queue ! "
        self._pipeline_description += gst_videoscale_server + " ! "
        self._pipeline_description += gst_encoding + " ! "
        self._pipeline_description += "udpsink port=" + str(self._server_port) + " host=" + str(self._server_ip) + "  "
        self._pipeline_description += "t. ! queue ! "
        self._pipeline_description += gst_videoscale_tracker + " ! "
        self._pipeline_description += gst_encoding + " ! "

        if self._my_ip != "0.0.0.0":
            self._pipeline_description += "udpsink port=" + str(self._my_port) + " host=" + str(self._my_ip) + "  "
        else:
            self._pipeline_description += "udpsink port=" + str(self._my_port) + "  "

        if self._monitor:
            self._pipeline_description += "t. ! queue ! fpsdisplaysink"

        args = ["gst-launch-1.0"]
        for arg in self._pipeline_description.split(" "):
            args.append(arg)

        self._set_process_args(args)
