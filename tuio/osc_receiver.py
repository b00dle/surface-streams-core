import multiprocessing
from pythonosc import dispatcher
from pythonosc import osc_server


class OscReceiver(object):
    def __init__(self, ip, port, osc_disp=dispatcher.Dispatcher()):
        self._server = osc_server.ThreadingOSCUDPServer((ip, port), osc_disp)
        self._server_process = multiprocessing.Process(target=self._server.serve_forever)

    def start(self):
        print("Serving OSC on {}".format(self._server.server_address))
        self._server_process.start()

    def terminate(self):
        print("Stopped Serving OSC on {}".format(self._server.server_address))
        self._server_process.terminate()
