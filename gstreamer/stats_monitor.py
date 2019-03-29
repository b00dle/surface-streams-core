from gi.repository import GObject


class UdpStatsMonitor(object):
    """
    Class monitoring bytes sent of a udpsink element this instance links to.
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
        self.file = file

    def link(self, pipeline, element_name):
        """
        Links instance to a udpsink in a GstPipeline
        :param pipeline: GstPipeline containing udpsink element to monitor
        :param element_name: name of udpsink element to monitor.
        :return:
        """
        self.stop()
        self._pipeline = pipeline
        self._element_name = element_name

    def unlink(self):
        """
        Cuts the link between this instance and the udpsink it is monitoring.
        :return:
        """
        self.stop()
        self._pipeline = None
        self._element_name = None

    def start(self):
        """
        Starts the monitoring process.
        :return:
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
        :return:
        """
        if not self._enabled:
            return
        self._enabled = False

    def _update(self):
        """
        Updates stats read from udpsink element linked to this instance.
        :return:
        """
        new_stats = self.pull_stats_from_element()
        if new_stats is None or not self._enabled:
            return
        bytes_per_second = new_stats["bytes-sent"] - self.stats["bytes-sent"]
        if bytes_per_second > 0:
            tag = self._pipeline.get_name() + "." + self._element_name
            print("> " + tag + " stats:", new_stats)
            print("  > bytes/s:", bytes_per_second)
            print("  > mbit/s:", (bytes_per_second * 8) / 1000000)
            with open(self.file, "a") as log_file:
                log_file.write(tag + "," + str(bytes_per_second) + "\n")
                log_file.close()
        self.stats = new_stats
        if self._enabled:
            GObject.timeout_add_seconds(1, self._update)

    def pull_stats_from_element(self):
        """
        Getter for currently linked udpsink GstElement stats
        :return: current stats as dict
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
        stats = {
            data.nth_field_name(n): data.get_value(data.nth_field_name(n))
            for n in range(0, data.n_fields())
        }
        return stats
