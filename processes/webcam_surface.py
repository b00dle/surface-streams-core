from processes import ProcessWrapper


class WebcamSurface(ProcessWrapper):
    def __init__(self, server_port, my_port, server_ip="0.0.0.0", my_ip="0.0.0.0", protocol="jpeg",
                 device="/dev/video0", server_stream_width=320, monitor=True,
                 input_adjustment={"saturation":2.0, "brightness":0.0}):
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
        gst_videoscale = "videoscale ! " \
                         "video/x-raw, width=" + str(self._server_stream_width) + ", " \
                         "pixel-aspect-ratio=1/1"

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
        #self._pipeline_description += "videobalance saturation=2.0 brightness=+0.1 ! "
        self._pipeline_description += "aspectratiocrop aspect-ratio=16/9 ! "
        self._pipeline_description += "tee name=t ! queue ! "
        self._pipeline_description += gst_videoscale + " ! "
        self._pipeline_description += gst_encoding + " ! "
        self._pipeline_description += "udpsink port=" + str(self._server_port) + " host=" + str(self._server_ip) + "  "
        self._pipeline_description += "t. ! queue ! "
        self._pipeline_description += gst_encoding + " ! "
        self._pipeline_description += "udpsink port=" + str(self._my_port) + " host=" + str(self._my_ip) + "  "
        if self._monitor:
            self._pipeline_description += "t. ! queue ! fpsdisplaysink"

        args = ["gst-launch-1.0"]
        for arg in self._pipeline_description.split(" "):
            args.append(arg)

        self._set_process_args(args)