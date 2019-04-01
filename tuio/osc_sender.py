from pythonosc import udp_client


class OscSender(object):
    """
    Base class for sending OSC messages over udp channel.
    """

    def __init__(self, ip, port):
        """
        Constructor.

        :param ip: ip to send messages to.

        :param port: port to send messages to.
        """
        self._client = udp_client.SimpleUDPClient(ip, port)

    def _send_message(self, path, arg_lst):
        """
        Sends message to OSC server host.

        :param path: OSC path (used by dispatcher on receiver side)

        :param arg_lst: argument list

        :return: None
        """
        self._client.send_message(path, arg_lst)
