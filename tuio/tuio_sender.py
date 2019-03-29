import argparse
import time

from pythonosc import udp_client
from typing import List
from tuio.tuio_elements import TuioImagePattern, TuioPointer, TuioData


class OscSender(object):
    def __init__(self, ip, port):
        self._client = udp_client.SimpleUDPClient(ip, port)

    def _send_message(self, path, arg_lst):
        self._client.send_message(path, arg_lst)


def extract_bnd_args(pattern: TuioImagePattern):
    return [
        pattern.get_s_id(),
        pattern.get_u_id(),
        pattern.get_bnd().x_pos,
        pattern.get_bnd().y_pos,
        pattern.get_bnd().angle,
        pattern.get_bnd().width,
        pattern.get_bnd().height,
    ]


def extract_sym_args(pattern: TuioImagePattern):
    return [
        pattern.get_s_id(),
        pattern.get_u_id(),
        pattern.get_sym().tu_id,
        pattern.get_sym().c_id,
        "uuid",
        pattern.get_sym().uuid
    ]


def extract_ptr_args(pointer: TuioPointer):
    return [
        pointer.s_id,
        pointer.u_id,
        pointer.tu_id,
        pointer.c_id,
        pointer.x_pos,
        pointer.y_pos,
        pointer.angle,
        pointer.shear,
        pointer.radius,
        pointer.press
    ]


def extract_dat_args(data: TuioData):
    return [
        data.mime_type,
        data.data
    ]


class TuioSender(OscSender):
    def __init__(self, ip, port):
        super().__init__(ip, port)

    def send_pattern(self, pattern: TuioImagePattern):
        if pattern.is_valid():
            self._send_message("/tuio2/bnd", extract_bnd_args(pattern))
            self._send_message("/tuio2/sym", extract_sym_args(pattern))

    def send_patterns(self, patterns: List[TuioImagePattern]):
        for p in patterns:
            self.send_pattern(p)

    def send_pointer(self, pointer: TuioPointer):
        if not pointer.is_empty():
            self._send_message("/tuio2/ptr", extract_ptr_args(pointer))
            for d in pointer.get_data():
                args = [pointer.s_id, pointer.u_id, pointer.c_id]
                for arg in extract_dat_args(d):
                    args.append(arg)
                self._send_message("/tuio2/dat", args)

    def send_pointers(self, pointers: List[TuioPointer]):
        for p in pointers:
            self.send_pointer(p)


def run_pattern_sender(ip="0.0.0.0", port=5001):
    from tuio.tuio_elements import TuioBounds, TuioSymbol
    import random
    import uuid

    patterns = [TuioImagePattern(u_id=random.randint(0, 500))
                for i in range(0, 10)]
    for p in patterns:
        x = random.randint(0, 10)
        y = 10 - x
        p.set_bnd(TuioBounds(x, y, 0, 10, 10))
        p.set_sym(TuioSymbol(str(uuid.uuid4())))

    client = TuioSender(ip, port)
    client.send_patterns(patterns)

    for x in range(0,10):
        p_idx = random.randint(0, len(patterns)-1)
        p = patterns[p_idx]
        p.set_x_pos(random.randint(0,15))
        p.set_y_pos(random.randint(0,7))
        client.send_pattern(p)
        time.sleep(1)


'''
minimum example of osc sender
'''


def run(ip="127.0.0.1", port=5005):
    client = udp_client.SimpleUDPClient(ip, port)

    for x in range(10):
        client.send_message("/foo", [x, "yo", True])
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--ip",
        default="127.0.0.1",
        help="The ip of the OSC server"
    )

    parser.add_argument(
        "--port", type=int, default=5005,
        help="The port the OSC server is listening on")

    args = parser.parse_args()

    run(args.ip, args.port)
