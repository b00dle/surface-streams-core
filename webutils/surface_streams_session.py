import requests

from core.webutils import api_helper


class SurfaceStreamsSession(object):
    """
    Wrapper for ReST API call based communication to a Surface Streams server. Helps establish a connection to the video
    mixing pipeline and receive tuio events from other remote clients participating in the session. Once connected, this
    class provides access to video stream input/output port, tuio input/output port, user id and uuid assigned for the
    connected client.

    For more info on Surface Streams 2.0 remote tracker see https://github.com/b00dle/surface-streams-remote-tracker.

    For more info on Surface Streams 2.0 client see https://github.com/b00dle/surface-streams-client.
    """

    def __init__(self, my_ip="0.0.0.0", name="client", video_src_port=5002, video_protocol="jpeg", mixing_mode="other"):
        """
        Constructor.

        :param my_ip: Ip address server should use to communicate with this client session.

        :param name: arbitrary string name to assign for this client.

        :param video_src_port: port at which server should expect video stream input. -1 means set by server. The final
        value can be read from this instance after calling self.connect(). (see self.get_video_src_port())

        :param video_protocol: protocol encoding used for video stream. Choose 'jpeg', 'vp8', 'vp9', 'mp4', 'h264' or
        'h265'

        :param mixing_mode: describes how client video streams should be mixed and sent back to clients. Choose 'all'
        for mixing every client stream, including the one sent by this session, or 'other' to mix all streams except the
        one sent by this session.
        """
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
        """
        Get the ip address the serve ris using to communicate with this session.

        :return: str
        """
        return self._my_ip

    def get_name(self):
        """
        Get the name assigned set for session.

        :return: str
        """
        return self._name

    def get_video_src_port(self):
        """
        Returns the port at which the server expects video stream input. Final value can be read after connecting this
        session. (see self.connect())

        :return: int
        """
        return self._video_src_port

    def get_video_sink_port(self):
        """
        Returns the port to which the server will send the merged video output streams. Final value can be read after
        connecting this session. (see self.connect())

        :return: int
        """
        return self._video_sink_port

    def get_tuio_sink_port(self):
        """
        Returns the port to which the server will send the merged tuio event streams. Final value can be read after
        connecting this session. (see self.connect())

        :return: int
        """
        return self._tuio_sink_port

    def get_video_protocol(self):
        """
        Returns the protocol encoding for the video streams send to and received from the Surface Streams 2.0 server.

        :return: str ('jpeg', 'vp8', 'vp9', 'mp4', 'h264' or 'h265')
        """
        return self._video_protocol

    def get_mixing_mode(self):
        """
        Returns how client video streams should be mixed for this client on the server side. 'all' means every client
        stream is overlayed and 'other' means the merged stream excludes the video stream sent by this session.

        :return: str ('all', 'other')
        """
        return self._mixing_mode

    def get_uuid(self):
        """
        Returns the uuid of this client session. Final value can be read after connecting this session. (see
        self.connect())

        :return: str
        """
        return self._uuid

    def get_id(self):
        """
        Returns the user id assigned to this session. Should be included in any tuio events forwarded into the
        application. Final value can be read after connecting this session. (see self.connect())

        :return: int
        """
        return self._id

    def connect(self):
        """
        Establishes a connection to the Surface Streams 2.0 server and registers the settings configured during
        initialization of this instance. Final values for video stream input/output port, tuio input/output port, user
        id and uuid will be available once connected. Furthermore, the server will be ready waiting for all input video
        streams.

        :return: Success of initialization.
        """
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
        """
        Unregister a running Surface Streams 2.0 server session. Make sure to call this function prior to calling
        __del__ or removing refs on this instance. Otherwise, the client session will not be cleared on the server side.

        :return: Success of clearing session
        """
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
