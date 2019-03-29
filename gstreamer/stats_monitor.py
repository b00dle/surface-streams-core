from gi.repository import GObject


class UdpStatsMonitor(object):
    def __init__(self):
        self.stats = {}
        self._enabled = False
        self._pipeline = None
        self._element_name = None

    def link(self, pipeline, element_name):
        self.stop()
        self._pipeline = pipeline
        self._element_name = element_name

    def unlink(self):
        self.stop()
        self._pipeline = None
        self._element_name = None

    def start(self):
        if self._enabled:
            return
        self.stats = self.pull_stats_from_element()
        self._enabled = True
        GObject.timeout_add_seconds(1, self._update)

    def stop(self):
        if not self._enabled:
            return
        self._enabled = False

    def _update(self):
        new_stats = self.pull_stats_from_element()
        if new_stats is None or not self._enabled:
            return
        bytes_per_second = new_stats["bytes-sent"] - self.stats["bytes-sent"]
        if bytes_per_second > 0:
            print("> " + self._pipeline.get_name() + "." + self._element_name + " stats:", new_stats)
            print("  > bytes/s:", bytes_per_second)
            print("  > mbit/s:", (bytes_per_second * 8) / 1000000)
        self.stats = new_stats
        if self._enabled:
            GObject.timeout_add_seconds(1, self._update)

    def pull_stats_from_element(self):
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