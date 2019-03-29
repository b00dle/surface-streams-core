from processes import ProcessWrapper


class ExecutableGstSurface(ProcessWrapper):
    """
    Class used to encapsulate execution of SurfaceStreams reconstruction
    and streaming data over udp channel.
    """

    def __init__(self, server_port, my_port, server_ip="0.0.0.0", my_ip="0.0.0.0", executable_path="./realsense", pre_gst_args=["!"], server_stream_width=320, protocol="jpeg", monitor=True):
        """
        Constructor.
        :param realsense_dir: directory where ./realsense executable can be found.
        Program can be found and built at https://github.com/floe/surface-streams
        :param protocol: encoding for udp stream. Choose 'jpeg', 'vp8', 'mp4' or 'h264'
        """
        super().__init__()
        self._server_ip = server_ip
        self._server_port = server_port
        self._server_stream_width = server_stream_width
        self._my_port = my_port
        self._my_ip = my_ip
        self._executable_path = executable_path
        self._pre_gst_args = pre_gst_args
        self._protocol = protocol
        self._monitor = monitor
        self._compute_launch_command()

    def _compute_launch_command(self):
        """
        Creates the subprocess creation call for realsense executable.
        Includes a GStreamer pipeline for streaming reconstruction over udp.
        :return:
        """
        height = self._server_stream_width * 9/16.0
        gst_videoscale = "videoscale ! video/x-raw, " \
                         "width=" + str(self._server_stream_width) + ", " \
                         "height=" + str(int(height))

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
            gst_encoding += "x264enc tune=zerolatency ! rtph264pay"
        elif self._protocol == "h265":
            gst_encoding += "x265enc tune=zerolatency ! rtph265pay"

        gst_launch_cmd = "queue ! videoconvert ! "
        gst_launch_cmd += "tee name=t ! queue ! "
        gst_launch_cmd += gst_videoscale + " ! "
        gst_launch_cmd += gst_encoding + " ! "
        gst_launch_cmd += "udpsink host=" + str(self._server_ip) + " port=" + str(self._server_port) + "  "
        gst_launch_cmd += "t. ! queue ! "
        gst_launch_cmd += gst_encoding + " ! "
        gst_launch_cmd += "udpsink host=" + str(self._my_ip) + " port=" + str(self._my_port)
        if self._monitor:
            gst_launch_cmd += "  t. ! queue ! fpsdisplaysink"

        args = []
        args.append(self._executable_path)
        args.extend(self._pre_gst_args)
        args.append(gst_launch_cmd)
        self._set_process_args(args)