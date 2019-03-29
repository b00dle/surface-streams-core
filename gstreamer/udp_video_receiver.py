import gstreamer
import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst, Gtk, GstVideo, GdkX11
from gstreamer.gst_pipeline import GstPipeline
from pprint import pprint


class UdpVideoReceiver(GstPipeline):
    '''
    Implements a GST pipeline to receive jpeg encoded rtp-gst frames over udp,
    decode them, convert them to video and produce output into
    an embedded gtksink window. Can handle multiple stream encodings (jpeg, vp8, mp4, h264).

    (default) gst pipeline description:
    gst-launch-1.0 udpsrc port=5000 ! application/x-rtp, media=application ! queue !
        rtpgstdepay ! jpegdec ! videoconvert ! gtksink
    '''

    def __init__(self, protocol="jpeg"):
        """
        Constructor.
        :param protocol: encoding of received stream. Choose 'jpeg', 'vp8', 'mp4' or 'h264'
        """
        super().__init__("Udp-Video-Receiver")
        self._protocol = protocol
        self._init_ui()
        self._init_gst_pipe()

    def _init_ui(self):
        """
        Helper function for Constructor to init UI elements.
        :return:
        """
        self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Udp Video Receiver")
        self.window.set_default_size(500, 400)
        self.window.connect("destroy", Gtk.main_quit, "WM destroy")
        self.vbox_layout = Gtk.VBox()
        self.window.add(self.vbox_layout)
        self.window.show_all()

    def _init_gst_pipe(self):
        """
        Helper function for Constructor to init GStreamer pipeline.
        :return:
        """
        # create necessary elements
        self.udp_src = self.make_add_element("udpsrc", "udpsrc")
        src_queue = self.make_add_element("queue", "src_queue")
        rtp_depay = None
        decoder = None
        if self._protocol == "jpeg":
            self.udp_src.set_property("caps", Gst.caps_from_string(gstreamer.JPEG_CAPS))
            rtp_depay = self.make_add_element("rtpgstdepay", "rtp_depay")
            decoder = self.make_add_element("jpegdec", "jpeg_decoder")
        elif self._protocol == "vp8":
            self.udp_src.set_property("caps", Gst.caps_from_string(gstreamer.VP8_CAPS))
            rtp_depay = self.make_add_element("rtpvp8depay", "v8_depay")
            decoder = self.make_add_element("vp8dec", "v8_decoder")
        elif self._protocol == "vp9":
            self.udp_src.set_property("caps", Gst.caps_from_string(gstreamer.VP9_CAPS))
            rtp_depay = self.make_add_element("rtpvp9depay", "v9_depay")
            decoder = self.make_add_element("vp9dec", "v9_decoder")
        elif self._protocol == "mp4":
            self.udp_src.set_property("caps", Gst.caps_from_string(gstreamer.MP4_CAPS))
            rtp_depay = self.make_add_element("rtpmp4vdepay", "mp4_depay")
            decoder = self.make_add_element("avdec_mpeg4", "mp4_decoder")
        elif self._protocol == "h264":
            self.udp_src.set_property("caps", Gst.caps_from_string(gstreamer.H264_CAPS))
            rtp_depay = self.make_add_element("rtph264depay", "h264_depay")
            decoder = self.make_add_element("avdec_h264", "h264_decoder")
        elif self._protocol == "h265":
            self.udp_src.set_property("caps", Gst.caps_from_string(gstreamer.H265_CAPS))
            rtp_depay = self.make_add_element("rtph265depay", "h265_depay")
            decoder = self.make_add_element("avdec_h264", "h265_decoder")
        videoconvert = self.make_add_element("videoconvert", "video_converter")
        videosink = self.make_add_element("gtksink", "videosink")
        self.vbox_layout.add(videosink.props.widget)
        videosink.props.widget.show()
        # link elements
        self.link_elements(self.udp_src, src_queue)
        self.link_elements(src_queue, rtp_depay)
        self.link_elements(rtp_depay, decoder)
        self.link_elements(decoder, videoconvert)
        self.link_elements(videoconvert, videosink)

    def start(self, port):
        """
        Starts receiving stream data on given port.
        :param port: port of the running systems udp socket.
        :return:
        """
        self.udp_src.set_property("port", port)
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_bus_message(self, bus, message):
        """
        BC override
        :param bus:
        :param message:
        :return:
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
                pprint(dir(message.src))
                print(msg_src)
        elif t == Gst.MessageType.EOS:
            print("reached end")
        elif t == Gst.MessageType.WARNING:
            wrn, debug = message.parse_warning()
            print(message.src.get_name() + " Warning: %s" % wrn, debug)
        else:
            print(t)