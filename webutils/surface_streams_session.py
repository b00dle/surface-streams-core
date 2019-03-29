import requests

from core.webutils import api_helper


class SurfaceStreamsSession(object):
    def __init__(self, my_ip="0.0.0.0", name="client", video_src_port=5002, video_protocol="jpeg", mixing_mode="other"):
        self._my_ip = my_ip
        self._name = name
        self._video_src_port = video_src_port
        self._video_protocol = video_protocol
        self._mixing_mode = mixing_mode
        self._is_connected = False
        # retrieved upon connecting
        self._video_sink_port = -1
        self._tuio_sink_port = -1
        self._uuid = None
        self._id = None

    def get_my_ip(self):
        return self._my_ip

    def get_name(self):
        return self._name

    def get_video_src_port(self):
        return self._video_src_port

    def get_video_sink_port(self):
        return self._video_sink_port

    def get_tuio_sink_port(self):
        return self._tuio_sink_port

    def get_video_protocol(self):
        return self._video_protocol

    def get_mixing_mode(self):
        return self._mixing_mode

    def get_uuid(self):
        return self._uuid

    def get_id(self):
        return self._id

    def connect(self):
        if self._is_connected:
            print("### FAILURE\n  > client already connected")
            return False
        r = requests.post("http://" + api_helper.SERVER_IP + ":5000/api/clients", data={}, json={
            "ip": self._my_ip,
            "video_src_port": self._video_src_port,
            "name": self._name,
            "video_sink_port": self._video_sink_port,
            "video_protocol": self._video_protocol,
            "tuio_sink_port": self._tuio_sink_port,
            "mixing_mode": self._mixing_mode
        })
        if r.status_code == 200:
            if r.headers['content-type'] == "application/json":
                data = r.json()
                self._video_src_port = data["video_src_port"]
                self._video_sink_port = data["video_sink_port"]
                self._tuio_sink_port = data["tuio_sink_port"]
                self._uuid = data["uuid"]
                self._id = data["id"]
                self._is_connected = True
                print("### SUCCESS connecting client\n  > data", data)
                print("  > Server is expecting video stream at udp port", data["video_src_port"])
                print("    > stream format should be", data["video_protocol"])
                print("  > Server is expecting tuio stream at udp port", 5001)
                print("  > Server is sending merged video stream to udp port", data["video_sink_port"])
                print("  > Server is sending merged tuio stream to udp port", data["tuio_sink_port"])
                print("  > USER ID assigned is", data["id"])
                print("###")
                return True
            else:
                raise ValueError("### API error\n > expecting response json")
        else:
            print("### HTTP error\n  > code", r.status_code)
            print("  > reason", r.reason)
            return False

    def disconnect(self):
        if not self._is_connected:
            print("### FAILURE\n  > client not connected")
            return False
        url = "http://" + api_helper.SERVER_IP + ":5000/api/clients/" + self._uuid
        r = requests.delete(url)
        if r.status_code == 200:
            print("### SUCCESS\n  > client disconnected")
            self._uuid = None
            return True
        else:
            print("### HTTP error\n  > code", r.status_code)
            print("  > reason", r.reason)
            return False
