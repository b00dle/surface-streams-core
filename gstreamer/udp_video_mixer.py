import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, GstVideo, GdkX11, Gtk
from core.gstreamer.gst_pipeline import GstPipeline
from core.gstreamer.stats_monitor import UdpStatsMonitor
from core import gstreamer


class UdpVideoMixer(GstPipeline):
    """
    Class Managing SurfaceStreams GStreamer pipeline.

    Can receive input from N clients over udp.

    For each client the pipeline overlays (using green keying) X-1 client streams (excluding stream sent by client)
    and sends merged streams back to client.

    Optionally, all X streams can be merged for a client. (see clients["mixing_mode"])
    """

    client_properties = [
        {
            "pattern": 0,
            "width": 1280,
            "height": 960
        },
        {
            "pattern": 1,
            "width": 640,
            "height": 480
        },
        {
            "pattern": 4,
            "width": 320,
            "height": 480
        }
    ]

    def __init__(self, clients, default_mode="other", width=640, height=480):
        """
        Constructor.

        :param clients: List of client dicts denoting client stream settings.
        For each client dict this instance will parse:
          - clients[i]["mixing_mode"] = "all" / "other"
            - "all" : overlay all streams (including clients own) when merging
            - "other" : exclude clients own stream when merging
          - clients[i]["video_protocol"] = "jpeg" / "vp8" / "vp9" / "mp4" / "h264" / "h265"

        :param default_mode: 'all' for overlaying all streams and
        'other' for merging other clients streams per client.

        :param width: pixel width of the output stream

        :param height: pixel height of the output stream
        """
        if default_mode != "other" and default_mode != "all":
            raise ValueError("Unknown mode '" + default_mode + "'n  > 'other' and 'all' are supported.")

        super().__init__("Udp-Multi-Video-Mixer")

        self.monitors = [
            UdpStatsMonitor("mixing-stats-"+str(i)+".txt")
            for i in range(0, len(clients))
        ]

        self.mixers = [
            self.make_add_element("videomixer", "mixer"+str(i))
            for i in range(0, len(clients))
        ]

        self.tees = [
            self.make_add_element("tee", "tee"+str(i))
            for i in range(0, len(clients))
        ]

        # create and link udpsrc inputs to tee
        self.src_bins = []
        for i in range(0, len(clients)):
            self.src_bins.append(self._create_src_bin(clients[i], i))

        # create and link tee inputs to mixer
        for i in range(0, len(clients)):
            for tee_idx in range(0, len(clients)):
                if tee_idx == i and len(clients) > 1 and clients[i]["mixing_mode"] == "other":
                    continue
                name_post_fix = str(i) + "-t" + str(tee_idx)
                mixer_queue = self.make_add_element("queue", "mixer_queue"+name_post_fix)
                videoscale = self.make_add_element("videoscale", "videoscale"+name_post_fix)
                capsfilter = self.make_add_element("capsfilter", "capsfilter"+name_post_fix)
                capsfilter.set_property("caps", Gst.caps_from_string("video/x-raw, width=" + str(width) + ", height=" + str(height) + ""))
                alpha = self.make_add_element("alpha", "alpha"+name_post_fix)
                alpha.set_property("method", "green")
                alpha.set_property("angle", 50)
                # get and link tee src pad to mixer queue sink pad
                tee_src_pad_template = self.tees[tee_idx].get_pad_template("src_%u")
                tee_src = self.tees[tee_idx].request_pad(tee_src_pad_template, None, None)
                mixer_queue_sink = mixer_queue.get_static_pad("sink")
                # link mixing pipeline
                self.link_elements(tee_src, mixer_queue_sink)
                self.link_elements(mixer_queue, videoscale)
                self.link_elements(videoscale, capsfilter)
                self.link_elements(capsfilter, alpha)
                self.link_elements(alpha, self.mixers[i])

        # create and link mixer outputs to udpsink
        self.sink_bins = []
        for i in range(0, len(clients)):
            self.sink_bins.append(self._create_sink_bin(clients[i], i))

        for i in range(0, len(clients)):
            self.monitors[i].link(
                self.pipeline,
                self.sink_bins[i]["udpsink"].get_name()
            )
            self.monitors[i].start()

    def _create_src_bin(self, client, i):
        """
        Helper function for constructor to build handling for stream input of 'i'th client.

        :param client: client dict descriptor

        :param i: client index (needed for naming purposes)

        :return: dict of GStreamer elements created
        """
        udp_src = self.make_add_element("udpsrc", "udpsrc" + str(i))
        src_queue = self.make_add_element("queue", "src_queue" + str(i))
        rtp_depay = None
        extra_parse = None
        decoder = None
        if client["video_protocol"] == "jpeg":
            # create elements
            udp_src.set_property("caps", Gst.caps_from_string(gstreamer.JPEG_CAPS))
            rtp_depay = self.make_add_element("rtpgstdepay", "rtp_depay" + str(i))
            decoder = self.make_add_element("jpegdec", "jpeg_decoder" + str(i))
        elif client["video_protocol"] == "vp8":
            # create elements
            udp_src.set_property("caps", Gst.caps_from_string(gstreamer.VP8_CAPS))
            rtp_depay = self.make_add_element("rtpvp8depay", "rtp_depay" + str(i))
            decoder = self.make_add_element("vp8dec", "vp8_decoder" + str(i))
        elif client["video_protocol"] == "vp9":
            # create elements
            udp_src.set_property("caps", Gst.caps_from_string(gstreamer.VP9_CAPS))
            rtp_depay = self.make_add_element("rtpvp9depay", "rtp_depay" + str(i))
            decoder = self.make_add_element("vp9dec", "vp9_decoder" + str(i))
        elif client["video_protocol"] == "mp4":
            # create elements
            udp_src.set_property("caps", Gst.caps_from_string(gstreamer.MP4_CAPS))
            rtp_depay = self.make_add_element("rtpmp4vdepay", "rtp_depay" + str(i))
            decoder = self.make_add_element("avdec_mpeg4", "mp4_decoder" + str(i))
        elif client["video_protocol"] == "h264":
            # create elements
            udp_src.set_property("caps", Gst.caps_from_string(gstreamer.H264_CAPS))
            rtp_depay = self.make_add_element("rtph264depay", "rtp_depay" + str(i))
            decoder = self.make_add_element("avdec_h264", "h264_decoder" + str(i))
        elif client["video_protocol"] == "h265":
            udp_src.set_property("caps", Gst.caps_from_string(gstreamer.H265_CAPS))
            rtp_depay = self.make_add_element("rtph265depay", "h265_depay" + str(i))
            extra_parse = self.make_add_element("h265parse", "extra_parse" + str(i))
            #extra_parse.set_property("disable-passthrough", True)
            #extra_parse.set_property("config-interval", 1)
            decoder = self.make_add_element("avdec_h265", "h265_decoder" + str(i))
        # link elements
        self.link_elements(udp_src, src_queue)
        self.link_elements(src_queue, rtp_depay)
        if extra_parse is not None:
            self.link_elements(rtp_depay, extra_parse)
            self.link_elements(extra_parse, decoder)
        else:
            self.link_elements(rtp_depay, decoder)
        self.link_elements(decoder, self.tees[i])
        # remember src bin
        return {
            "udpsrc": udp_src,
            "queue": src_queue,
            "rtp_depay": rtp_depay,
            "extra_parse": extra_parse,
            "decoder": decoder
        }

    def _create_sink_bin(self, client, i):
        """
        Helper function for constructor to build handling for stream output of ith client.

        :param client: client dictionary descriptor (see self.__init__(clients, ...))

        :param i: client index (needed for naming purposes)

        :return: dictionary of GStreamer elements created
        """
        queue_out = self.make_add_element("queue", "queue_out" + str(i))
        videoconvert = self.make_add_element("videoconvert", "mixer_convert" + str(i))
        encoder = None
        rtp_packer = None
        if client["video_protocol"] == "jpeg":
            encoder = self.make_add_element("jpegenc", "jpeg_encoder" + str(i))
            rtp_packer = self.make_add_element("rtpgstpay", "rtp_packer" + str(i))
        elif client["video_protocol"] == "vp8":
            encoder = self.make_add_element("vp8enc", "vp8_encoder" + str(i))
            #encoder.set_property("target-bitrate", 4096*1000)
            rtp_packer = self.make_add_element("rtpvp8pay", "rtp_packer" + str(i))
        elif client["video_protocol"] == "vp9":
            encoder = self.make_add_element("vp9enc", "vp9_encoder" + str(i))
            rtp_packer = self.make_add_element("rtpvp9pay", "rtp_packer" + str(i))
        elif client["video_protocol"] == "mp4":
            encoder = self.make_add_element("avenc_mpeg4", "mp4_encoder" + str(i))
            rtp_packer = self.make_add_element("rtpmp4vpay", "rtp_packer" + str(i))
            rtp_packer.set_property("config-interval", 3)
        elif client["video_protocol"] == "h264":
            encoder = self.make_add_element("x264enc", "h264_encoder" + str(i))
            encoder.set_property("tune", "zerolatency")
            encoder.set_property("speed-preset", 4) # 1 fast but low encoding to 2 slow but high encoding
            encoder.set_property("pass", 5)
            encoder.set_property("quantizer", 22)
            rtp_packer = self.make_add_element("rtph264pay", "rtp_packer" + str(i))
        elif client["video_protocol"] == "h265":
            encoder = self.make_add_element("x265enc", "h265_encoder" + str(i))
            encoder.set_property("tune", "zerolatency")
            encoder.set_property("log-level", "full")
            rtp_packer = self.make_add_element("rtph265pay", "rtp_packer" + str(i))
        udp_sink = self.make_add_element("udpsink", "udp_sink" + str(i))
        # link mixer pipeline
        self.link_elements(self.mixers[i], queue_out)
        self.link_elements(queue_out, videoconvert)
        self.link_elements(videoconvert, encoder)
        self.link_elements(encoder, rtp_packer)
        self.link_elements(rtp_packer, udp_sink)
        # remember sink bin
        return {
            "queue": queue_out,
            "videoconvert": videoconvert,
            "encoder": encoder,
            "rtppay": rtp_packer,
            "udpsink": udp_sink
        }

    def cleanup(self):
        """
        BC override.
        """
        for monitor in self.monitors:
            monitor.unlink()
        super().cleanup()

    def set_in_port(self, port, client_idx):
        """
        Sets port for udpsrc (GstElement) of client referenced by client_idx.

        :param port: port of server udp socket to receive input at.

        :param client_idx: index identifying client in client list (as set by self.__init__(clients, ...))

        :return: None
        """
        self.src_bins[client_idx]["udpsrc"].set_property("port", port)

    def set_out_address(self, address, client_idx):
        """
        Sets destination IP-address for udpsink (GstElement) of client referenced by client_idx.

        :param address: IP of client udp address

        :param client_idx: index identifying client in client list (as set by self.__init__(clients, ...))

        :return: None
        """
        self.sink_bins[client_idx]["udpsink"].set_property("host", address)

    def set_out_port(self, port, client_idx):
        """
        Sets destination port for udpsink of client referenced by client_idx.

        :param port: port of client udp address

        :param client_idx: num identifying client

        :return: None
        """
        self.sink_bins[client_idx]["udpsink"].set_property("port", port)

    def on_udp_bus_message(self, bus, message):
        """
        BC override.
        """
        print("### on_udp_bus_message")
        print("  > message.src", message.src.get_name())

    def on_bus_message(self, bus, message):
        """
        BC override.
        """
        t = message.type
        if t == Gst.MessageType.STREAM_START:
            print("stream start")
            #self.pipeline.set_state(Gst.State.PLAYING)
        elif t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print(message.src.get_name()+" Error: %s" % err, debug)
        elif t == Gst.MessageType.STATE_CHANGED:
            old_state, new_state, pending_state = message.parse_state_changed()
            print(message.src.get_name()+" state changed from %s to %s." %
                  (old_state.value_nick, new_state.value_nick))
        elif t == Gst.MessageType.ELEMENT:
            msg_src = message.src.get_name()
            if "udp" in msg_src:
                print(msg_src)
        elif t == Gst.MessageType.EOS:
            print("reached end")
        elif t == Gst.MessageType.WARNING:
            wrn, debug = message.parse_warning()
            print(message.src.get_name() + " Warning: %s" % wrn, debug)
        else:
            print(t)
