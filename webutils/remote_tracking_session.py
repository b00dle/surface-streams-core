import requests

from core.webutils import api_helper
from core.tuio.tuio_tracking_config_parser import TuioTrackingConfigParser


class RemoteTrackingSession(object):
    def __init__(self, tracking_server_ip="0.0.0.0", tracking_server_port=9000,
                 surface_streams_server_ip="0.0.0.0", surface_streams_server_tuio_port=5001,
                 frame_width=640, frame_protocol="jpeg",
                 patterns_config="", user_id=-1):
        self._tracking_server_ip = tracking_server_ip
        self._tracking_server_port = tracking_server_port
        self._surface_streams_server_ip = surface_streams_server_ip
        self._surface_streams_server_tuio_port = surface_streams_server_tuio_port
        self._frame_width = frame_width
        self._frame_protocol = frame_protocol
        self._patterns_config = patterns_config
        self._user_id = user_id
        self._is_connected = False
        # received upon connecting
        self._uuid = None
        self._frame_port = -1

    def get_uuid(self):
        return self._uuid

    def get_frame_port(self):
        return self._frame_port

    def get_tracking_server_url(self):
        return "http://" + self._tracking_server_ip + ":" + str(self._tracking_server_port)

    def get_patterns_config(self):
        return self._patterns_config

    def set_patterns_config(self, path):
        self._patterns_config = path
        if len(self._patterns_config) > 0:
            api_helper.upload_tracking_config(
                self._uuid, self.get_tracking_server_url(), self._patterns_config
            )
            print("RemoteTrackingSession: Tracking config uploaded from", self._patterns_config)

    def connect(self):
        if self._is_connected:
            print("### FAILURE\n  > client already connected")
            return False

        tracking_url = self.get_tracking_server_url()

        r = requests.post(tracking_url + "/api/processes", data={}, json={
            "frame_port": self._frame_port,
            "frame_protocol": self._frame_protocol,
            "frame_width": self._frame_width,
            "server_ip": self._surface_streams_server_ip,
            "tuio_port": self._surface_streams_server_tuio_port,
            "user_id": self._user_id
        })
        if r.status_code == 200:
            if r.headers['content-type'] == "application/json":
                data = r.json()
                self._frame_port = data["frame_port"]
                self._surface_streams_server_tuio_port = data["tuio_port"]
                self._uuid = data["uuid"]
                self._user_id = data["user_id"]
                self._is_connected = True
                print("### SUCCESS connecting remote tracking\n  > data", data)
                print("  > Server is expecting video stream at udp port", data["frame_port"])
                print("    > stream format should be", data["frame_protocol"])
                print("  > Server is forwarding tuio data to", data["server_ip"])
                print("    > at port", data["tuio_port"])
                print("  > USER ID assigned is", data["user_id"])
                if len(self._patterns_config) > 0:
                    # upload all resources necessary to setup tracking
                    parser = TuioTrackingConfigParser(self._patterns_config)
                    for resource in parser.get_full_resource_paths():
                        api_helper.upload_tracking_resource(self._uuid, tracking_url, resource)
                        print("  > Resource uploaded at", resource)
                    # upload tracking config (will start tracking if successful)
                    api_helper.upload_tracking_config(self._uuid, tracking_url, self._patterns_config)
                    print("  > Tracking config uploaded from", self._patterns_config)
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
            print("### FAILURE\n  > remote tracking not connected")
            return False
        url = self.get_tracking_server_url() + "/api/processes/" + self._uuid
        r = requests.delete(url)
        if r.status_code == 200:
            print("### SUCCESS\n  > remote tracking disconnected")
            self._uuid = None
            return True
        else:
            print("### HTTP error\n  > code", r.status_code)
            print("  > reason", r.reason)
            return False
