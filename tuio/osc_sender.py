from pythonosc import udp_client


class OscSender(object):
    def __init__(self, ip, port):
        self._client = udp_client.SimpleUDPClient(ip, port)

    def _send_message(self, path, arg_lst):
        self._client.send_message(path, arg_lst)

def run(ip="127.0.0.1", port=5005):
    client = udp_client.SimpleUDPClient(ip, port)

    for x in range(10):
        client.send_message("/foo", [x, "yo", True])
        time.sleep(1)
