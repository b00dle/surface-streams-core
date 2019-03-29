import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst


class GstPipeline(object):
    def __init__(self, name):
        self.pipeline = Gst.Pipeline.new(name)
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.enable_sync_message_emission()
        self.bus.connect("message", self.on_bus_message)
        self.bus.connect("sync-message::element", self.on_bus_sync_message)

    def __del__(self):
        self.pipeline.set_state(Gst.State.NULL)

    def cleanup(self):
        pass

    def on_bus_message(self, bus, message):
        """ override in derived classes for message handling. """
        pass

    def on_bus_sync_message(self, bus, message):
        """ override in derived classes for sync message handling. """
        pass

    def make_add_element(self, gst_element_name, name):
        """
        Creates a GstElement with given gst_element_name
        and given name. The element is added to the pipeline
        and then returned.
        """
        gst_element = Gst.ElementFactory.make(gst_element_name, name)
        self.pipeline.add(gst_element)
        return gst_element

    def link_elements(self, src, sink):
        """ Links src-pad of src GstElement to sink-pad of sink GstElement. """
        if not src.link(sink):
            print("## link_elements")
            print(" > could not link")
            print("  > src", src.get_name())
            print("  > sink", sink.get_name())

    def register_callback(self, gst_element, signal_name, function):
        """
        Connects callback function to signal referenced by signal_name
        of given GstElement.
        """
        gst_element.connect(signal_name, function)