import os
import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst, Gtk, GstVideo, GdkX11, GObject
from gstreamer.gst_pipeline import GstPipeline
from gstreamer.stats_monitor import UdpStatsMonitor


class UdpVideoSender(GstPipeline):
    """
    Class encapsulating a filesrc based GStreamer pipeline streaming video data over udp.
    """

    def __init__(self, protocol="jpeg"):
        """
        Constructor.
        :param protocol: Choose 'jpeg', 'vp8', 'mp4' or 'h264' to configure encoding of stream
        """
        super().__init__("Udp-Video-Sender")
        self._protocol = protocol
        self._init_ui()
        self._init_gst_pipe()
        self.monitor = UdpStatsMonitor()
        self.monitor.link(self.pipeline, "udp_sink")

    def cleanup(self):
        """ Cleans up all instance refs. Should be called prior to __del__. """
        self.monitor.unlink()

    def _init_ui(self):
        """
        Constructor helper to create UI structure.
        :return:
        """
        self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Udp Video Sender")
        self.window.set_default_size(500, 400)
        self.window.connect("destroy", Gtk.main_quit, "WM destroy")
        self.vbox_layout = Gtk.VBox()
        self.window.add(self.vbox_layout)
        hbox_layout = Gtk.HBox()
        self.vbox_layout.pack_start(hbox_layout, False, False, 0)
        self.entry = Gtk.Entry()
        self.entry.set_text("/home/basti/Documents/studium/master/green-sample.mp4")
        hbox_layout.add(self.entry)
        self.button = Gtk.Button("Start")
        hbox_layout.pack_start(self.button, False, False, 0)
        self.button.connect("clicked", self.start_stop)
        self.window.show_all()

    def _init_gst_pipe(self):
        """
        Constructor helper to create GStreamer pipeline.
        :return:
        """
        # create necessary elements
        self.filesrc = self.make_add_element("filesrc", "filesrc")
        decoder = self.make_add_element("decodebin", "decoder")
        self.queue = self.make_add_element("queue", "decode_queue")
        converter = self.make_add_element("videoconvert", "converter")
        tee = self.make_add_element("tee", "tee")
        ## sending pipeline
        udp_queue = self.make_add_element("queue", "udp_queue")
        encoder = None
        rtp_packer = None
        if self._protocol == "jpeg":
            encoder = self.make_add_element("jpegenc", "jpeg_encoder")
            rtp_packer = self.make_add_element("rtpgstpay", "rtp_packer")
        elif self._protocol == "vp8":
            encoder = self.make_add_element("vp8enc", "vp8_encoder")
            #encoder.set_property("target-bitrate", 4096*1000)
            rtp_packer = self.make_add_element("rtpvp8pay", "rtp_packer")
        elif self._protocol == "vp9":
            encoder = self.make_add_element("vp9enc", "vp9_encoder")
            rtp_packer = self.make_add_element("rtpvp9pay", "rtp_packer")
        elif self._protocol == "mp4":
            encoder = self.make_add_element("avenc_mpeg4", "mp4_encoder")
            rtp_packer = self.make_add_element("rtpmp4vpay", "rtp_packer")
            rtp_packer.set_property("config-interval", 3)
        elif self._protocol == "h264":
            encoder = self.make_add_element("x264enc", "h264_encoder")
            encoder.set_property("tune", "zerolatency")
            encoder.set_property("speed-preset", 4)  # 1 fast but low encoding to 2 slow but high encoding
            encoder.set_property("pass", 5)
            encoder.set_property("quantizer", 22)
            rtp_packer = self.make_add_element("rtph264pay", "rtp_packer")
        elif self._protocol == "h265":
            encoder = self.make_add_element("x265enc", "h265_encoder")
            encoder.set_property("tune", "zerolatency")
            encoder.set_property("log-level", "full")
            rtp_packer = self.make_add_element("rtph265pay", "rtp_packer")
        self.udp_sink = self.make_add_element("udpsink", "udp_sink")
        ## display pipeline
        video_queue = self.make_add_element("queue", "video_queue")
        converter2 = self.make_add_element("videoconvert", "converter2")
        videosink = self.make_add_element("gtksink", "videosink")
        self.vbox_layout.add(videosink.props.widget)
        videosink.props.widget.show()

        # connect element signals
        self.register_callback(decoder, "pad-added", self._decoder_pad_added)

        # setup pipeline links
        self.link_elements(self.filesrc, decoder)
        # link queue to converter through to udp sink
        # note: queue will be dynamically linked once pad is added on decoder
        # (see self.decoder_pad_added)
        self.link_elements(self.queue, converter)
        self.link_elements(converter, tee)
        ## link end of sending pipeline
        self.link_elements(udp_queue, encoder)
        self.link_elements(encoder, rtp_packer)
        self.link_elements(rtp_packer, self.udp_sink)
        ## link end of videosink pipeline
        self.link_elements(video_queue, converter2)
        self.link_elements(converter2, videosink)
        # setup tee links
        tee_src_pad_template = tee.get_pad_template("src_%u")
        tee_udp_pad = tee.request_pad(tee_src_pad_template, None, None)
        udp_queue_pad = udp_queue.get_static_pad("sink")
        tee_video_pad = tee.request_pad(tee_src_pad_template, None, None)
        video_queue_pad = video_queue.get_static_pad("sink")
        self.link_elements(tee_udp_pad, udp_queue_pad)
        self.link_elements(tee_video_pad, video_queue_pad)

    def set_port(self, port):
        """
        Sets stream destination port
        :param port: port of destination udp socket.
        :return:
        """
        self.udp_sink.set_property("port", port)

    def set_host(self, host):
        """
        Sets stream destination IP-address.
        :param host: IP of destination udp socket.
        :return:
        """
        self.udp_sink.set_property("host", host)

    def on_bus_message(self, bus, message):
        """ Resets Start button based on playback/error state. """
        t = message.type
        if t == Gst.MessageType.EOS:
            self._pipeline_stop()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
            self._pipeline_stop()

    def on_bus_sync_message(self, bus, message):
        pass
        '''
        message_name = message.get_structure().get_name()
        if message_name == "prepare-window-handle":
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_window_handle(self.movie_window.get_property("window").get_xid())
        '''

    def start_stop(self, w):
        """
        Toggles filesrc playback depending on current play state.
        :param w:
        :return:
        """
        if self.button.get_label() == "Start":
            filepath = self.entry.get_text().strip()
            if os.path.isfile(filepath):
                filepath = os.path.realpath(filepath)
                self.filesrc.set_property("location", filepath)
                self._pipeline_start()
            else:
                print("given path is no file")
        else:
            self._pipeline_stop()

    def _pipeline_stop(self):
        """
        Helper function to trigger pipeline state change to NULL
        and stop stats monitoring.
        :return:
        """
        self.pipeline.set_state(Gst.State.NULL)
        self.button.set_label("Start")
        self.monitor.stop()

    def _pipeline_start(self):
        """
        Helper function to trigger pipeline state change to PLAYING
        and start stats monitoring.
        :return:
        """
        self.button.set_label("Stop")
        self.pipeline.set_state(Gst.State.PLAYING)
        self.monitor.start()

    def _decoder_pad_added(self, decoder, pad):
        """
        Callback function to link decoder src pad to queue sink pad
        once the decoder receives input from the filesrc.
        :param decoder: GstElement triggering this callback
        :param pad: pad of GstElement that was added.
        :return:
        """
        template_property = pad.get_property("template")
        template_name = template_property.name_template
        # template name may differ for other decoders/demuxers
        if template_name == "src_%u":
            # link to video queue sink
            queue_sink = self.queue.sinkpads[0]
            self.link_elements(pad, queue_sink)