from gi.repository import GObject, Gst


class UdpStatsMonitor(object):
    """
    Class monitoring bytes & frames sent from a udpsink element this instance links to.
    Produces console logs for monitored data. Can also store data to csv file.
    """

    def __init__(self, file=""):
        """
        Constructor.
        :param file: optional .txt file path to store monitored data to in csv format.
        """
        self.stats = {}
        self._enabled = False
        self._pipeline = None
        self._element_name = None
        self._pad_probe_id = None
        self._num_buffers = 0
        self.file = file

    def link(self, pipeline, element_name):
        """
        Links this instance to a udpsink (GstElement) in given pipeline (GstPipeline)
        :param pipeline: GstPipeline containing udpsink (GstElement) to monitor
        :param element_name: name of udpsink (GstElement) to monitor.
        :return: None
        """
        self.stop()
        self._pipeline = pipeline
        self._element_name = element_name

    def unlink(self):
        """
        Cuts the link between this instance and the udpsink (GstElement) it is monitoring.
        :return: None
        """
        self.stop()
        self._pipeline = None
        self._element_name = None

    def start(self):
        """
        Starts the monitoring process.
        :return: None
        """
        if self._enabled:
            return
        self.stats = self.pull_stats_from_element()
        self._enabled = True
        if len(self.file) > 0:
            with open(self.file, "w") as log_file:
                log_file.write("name,bytes per second\n")
                log_file.close()
        GObject.timeout_add_seconds(1, self._update)

    def stop(self):
        """
        Stops the monitoring process.
        :return: None
        """
        if not self._enabled:
            return
        self._enabled = False
        if self._pad_probe_id is not None:
            element = self._pipeline.get_by_name(self._element_name)
            element.get_static_pad("sink").remove_probe(self._pad_probe_id)
            self._pad_probe_id = None
            self._num_buffers = 0

    def _increment_buffer_count(self, pad, buf):
        """
        This function increments the monitored count of buffers probed
        :param pad: gst pad probed
        :param buf: buffer retrieved from probe
        :return:
        """
        self._num_buffers += 1
        return True

    def _update(self):
        """
        Updates stats read from udpsink (GstElement) linked to this instance.
        :return: None
        """
        new_stats = self.pull_stats_from_element()
        if new_stats is None or not self._enabled:
            return
        bytes_per_second = new_stats["bytes-sent"] - self.stats["bytes-sent"]
        frames_per_second = new_stats["frames-sent"] - self.stats["frames-sent"]
        if bytes_per_second > 0:
            tag = self._pipeline.get_name() + "." + self._element_name
            print("> " + tag + " stats:", new_stats)
            print("  > bytes/s:", bytes_per_second)
            print("  > mbit/s:", (bytes_per_second * 8) / 1000000)
            print("  > fps:", frames_per_second)
            with open(self.file, "a") as log_file:
                log_file.write(tag + "," + str(bytes_per_second) + "\n")
                log_file.close()
        self.stats = new_stats
        if self._enabled:
            GObject.timeout_add_seconds(1, self._update)

    def pull_stats_from_element(self):
        """
        Getter for currently linked udpsink (GstElement) stats
        :return: current stats as dictionary
        """
        if self._pipeline is None or self._element_name is None:
            self._enabled = False
            return None
        element = self._pipeline.get_by_name(self._element_name)
        data = element.emit(
            "get_stats",
            element.get_property("host"),
            element.get_property("port")
        )
        if self._pad_probe_id is None:
            self._pad_probe_id = element.get_static_pad("sink").add_probe(
                Gst.PadProbeType.DATA_DOWNSTREAM, self._increment_buffer_count)
        stats = {
            data.nth_field_name(n): data.get_value(data.nth_field_name(n))
            for n in range(0, data.n_fields())
        }
        stats["frames-sent"] = self._num_buffers
        return stats
