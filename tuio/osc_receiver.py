import multiprocessing
from pythonosc import dispatcher
from pythonosc import osc_server


class OscReceiver(object):
    """
    Base class for receiving OSC messages over udp.
    """

    def __init__(self, ip, port, osc_disp=dispatcher.Dispatcher()):
        """
        Constructor.

        :param ip: address of the server instance.

        :param port: port of the server instance.

        :param osc_disp: pythonosc.dispatcher.Dispatcher instance handling incoming osc messages.
        """
        self._server = osc_server.ThreadingOSCUDPServer((ip, port), osc_disp)
        self._server_process = multiprocessing.Process(target=self._server.serve_forever)

    def start(self):
        """
        Starts server instance.

        :return: None
        """
        print("Serving OSC on {}".format(self._server.server_address))
        self._server_process.start()

    def terminate(self):
        """
        Stops server instance.

        :return: None
        """
        print("Stopped Serving OSC on {}".format(self._server.server_address))
        self._server_process.terminate()
