from core.processes import ProcessWrapper


class ExecutableGstSurface(ProcessWrapper):
    """
    Class used to encapsulate execution of Surface Streams reconstruction and streaming process. Reconstructed data is
    send over udp using Gstreamer.

    The idea here is, that the user can define the path to an executable able to produce a Gstreamer pipeline, which
    forwards video output to a udpsink (GstElement). Thus, this class can be used as an input process of a client in
    the Surface Streams 2.0 architecture.

    Examples of such reconstruction & streaming applications can be found at https://github.com/floe/surface-streams.

    The pipeline construction should support cmd calls of the following form (example):

    <path-to>/my-gst-executable ! "jpegenc ! rtpgstpay ! udpsink port=9999"

    (check out https://github.com/b00dle/surface-streams-client for full Surface Streams 2.0 client usage scenario.)
    """

    def __init__(self, server_port, my_port, server_ip="0.0.0.0", my_ip="0.0.0.0", executable_path="./realsense", pre_gst_args=["!"], server_stream_width=320, protocol="jpeg", monitor=True):
        """
        Constructor.

        :param server_port: udpsink (GstElement) port. In a Surface Streams 2.0 setup this should be where the server
        expects frame input from the client.

        :param my_port: secondary udpsink (GstElement) port. In a Surface Streams 2.0 setup this should be where the
        pattern matching process expects input.

        :param server_ip: udpsink (GstElement) ip. In a Surface Streams 2.0 setup this should be the server ip
        establishing streaming between all clients.

        :param my_ip: secondary udpsink (GstElement) ip. In a Surface Streams 2.0 setup this should be the ip address of
        the pattern matching process. For local tracking scenarios choose 0.0.0.0, else choose remote machine ip.

        :param executable_path: path to the executable capable of producing gstreamer output.
        example: executable_path ! "jpegenc ! rtpgstpay ! udpsink port=9999"

        :param pre_gst_args: Additional cmd parameters for executable call, added prior to gst pipeline.
        example: executable_path *pre_gst_args "jpegenc ! rtpgstpay ! udpsink port=9999"

        :param server_stream_width: width of the frame sent to server_ip:server_port

        :param protocol: frame protocol encoding. Choose 'jpeg', 'vp8', 'vp9', 'mp4', 'h264' or 'h265'

        :param monitor: if True an fpsdisplaysink (GstElement) will produce additional output of the pipeline produced
        by the executable.
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
        BC override.
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
