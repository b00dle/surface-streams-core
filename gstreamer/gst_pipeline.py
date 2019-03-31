import os
import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst, Gtk, GObject


class GstPipeline(object):
    """
    Base class for GStreamer pipeline implementations.
    """

    def __init__(self, name, debug=True):
        """
        Constructor.
        :param name: name of the pipeline
        :param debug: bool denoting whether debugging features should be enabled.
        If true pipeline will be plotted to dot file and pdf.
        """
        GObject.threads_init()
        Gst.init(None)
        self.registered_callbacks = {}
        self.pipeline = None
        self.bus = None
        self.pipeline = Gst.Pipeline.new(name)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.register_callback(self.bus, "message", self.on_bus_message)
        self.register_callback(self.bus, "sync-message::element", self.on_bus_sync_message)
        self.debug = debug
        self.name = name

    def __del__(self):
        print("##########deleting")
        if self.pipeline != None:
            self.pipeline.set_state(Gst.State.NULL)

    def dump_graph(self, output_dir="."):
        """
        Produces .dot and .pdf file of pipeline graph.
        :return:
        """
        dotfile = os.path.join(output_dir, self.name+".dot")
        if os.access(dotfile, os.F_OK):
            os.remove(dotfile)
        pdffile = os.path.join(output_dir, self.name+".pdf")
        Gst.debug_bin_to_dot_file(
            self.pipeline,
            Gst.DebugGraphDetails.ALL,
            self.name
        )
        os.system("dot -Tpdf " + dotfile + " -o " + pdffile)

    def start(self):
        """
        Changes state of GStreamer pipeline to PLAYING.
        Dumps graph (see dump_graph) if debug is enabled.
        :return:
        """
        self.pipeline.set_state(Gst.State.PLAYING)
        if self.debug:
            print("### PIPELINE GRAPH dumped")
            self.dump_graph()

    def stop(self):
        """
        Changes state of GStreamer pipeline to NULL.
        :return:
        """
        self.pipeline.set_state(Gst.State.NULL)

    def cleanup(self):
        """
        Unregisters all message callbacks and cleans up refs.
        Should be called prior to calling __del__ on instance.
        :return:
        """
        print("##########cleaning up")
        if len(self.registered_callbacks) > 0:
            for gst_element, callbacks in self.registered_callbacks.items():
                for c_id in callbacks:
                    gst_element.disconnect(c_id)
            self.registered_callbacks = {}
        self.bus.disable_sync_message_emission()
        self.bus.remove_signal_watch()
        self.stop()

    def on_bus_message(self, bus, message):
        """
        Bus massage callback.
        Override in derived classes for message handling.
        :return:
        """
        pass

    def on_bus_sync_message(self, bus, message):
        """
        Bus sync-massage callback.
        Override in derived classes for message handling.
        :return:
        """
        pass

    def make_add_element(self, gst_element_name, name):
        """
        Creates a GstElement with given gst_element_name
        and given name. The element is added to the pipeline
        and then returned.
        :param gst_element_name: name of element to add
        :param name: unqiue name for element instance
        :return: GStreamer element added
        """
        gst_element = Gst.ElementFactory.make(gst_element_name, name)
        self.pipeline.add(gst_element)
        return gst_element

    def link_elements(self, src, sink):
        """
        Links src-pad of src GstElement to sink-pad of sink GstElement.
        :param src: src pad of GstElement producing data
        :param sink: sink pad of GstElement receiving data
        :return:
        """
        if not src.link(sink):
            print("## link_elements")
            print(" > could not link")
            print("  > src", src.get_name())
            print("  > sink", sink.get_name())

    def register_callback(self, gst_element, signal_name, function):
        """
        Connects callback function to signal referenced by signal_name
        of given GstElement.
        :param gst_element: GstElement producing signal
        :param signal_name: name of GstElement signal
        :param function: callback function to connect signal to
        :return:
        """
        if gst_element not in self.registered_callbacks:
            self.registered_callbacks[gst_element] = []
        self.registered_callbacks[gst_element].append(
            gst_element.connect(signal_name, function)
        )
