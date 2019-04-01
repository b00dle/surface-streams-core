import argparse
import time

from typing import List
from core.tuio.tuio_elements import TuioImagePattern, TuioPointer, TuioData
from core.tuio.osc_sender import OscSender


def extract_bnd_args(pattern: TuioImagePattern):
    """
    Extracts list of bounds properties from TuioImagePattern, as formatted in tuio2 bnd message.

    :param pattern: TuioImagePattern containing bounds to extract data from

    :return: list of properties
    """
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
    """
    Extracts list of symbold identifier properties from TuioImagePattern, as formatted in tuio2 sym message.

    :param pattern: TuioImagePattern containing symbol identifier to extract data from

    :return: list of properties
    """
    return [
        pattern.get_s_id(),
        pattern.get_u_id(),
        pattern.get_sym().tu_id,
        pattern.get_sym().c_id,
        "uuid",
        pattern.get_sym().uuid
    ]


def extract_ptr_args(pointer: TuioPointer):
    """
    Extracts list of properties from TuioPointer, as formatted in tuio2 ptr message.

    :param pattern: TuioPointer to extract data from

    :return: list of properties
    """
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
    """
    Extracts list of data properties from TuioData, as formatted in tuio2 dat message.

    :param pattern: TuioData to extract data from

    :return: list of properties
    """
    return [
        data.mime_type,
        data.data
    ]


class TuioSender(OscSender):
    """
    Extends OscSender (see tuio/osc_sender.py) to send tuio 2.0 bnd, sym, ptr & dat messages.
    """

    def __init__(self, ip, port):
        """
        Constructor.

        :param ip: ip to send messages to.

        :param port: port to send messages to.
        """
        super().__init__(ip, port)

    def send_pattern(self, pattern: TuioImagePattern):
        """
        Constructs and sends a bnd & sym message from a TuioImagePattern

        :param pattern: TuioImagePattern to send

        :return: None
        """
        if pattern.is_valid():
            self._send_message("/tuio2/bnd", extract_bnd_args(pattern))
            self._send_message("/tuio2/sym", extract_sym_args(pattern))

    def send_patterns(self, patterns: List[TuioImagePattern]):
        """
        Constructs and send bnd & sym messages from list of TuioImagePattern instances.

        :param patterns: list of TuioImagePattern instances to send

        :return: None
        """
        for p in patterns:
            self.send_pattern(p)

    def send_pointer(self, pointer: TuioPointer):
        """
        Constructs and sends a ptr & dat message from a TuioPointer

        :param pointer: TuioPointer to send

        :return: None
        """
        if not pointer.is_empty():
            self._send_message("/tuio2/ptr", extract_ptr_args(pointer))
            for d in pointer.get_data():
                args = [pointer.s_id, pointer.u_id, pointer.c_id]
                for arg in extract_dat_args(d):
                    args.append(arg)
                self._send_message("/tuio2/dat", args)

    def send_pointers(self, pointers: List[TuioPointer]):
        """
        Constructs and send ptr & dat messages from list of TuioPointer instances.

        :param pointers: list of TuioPointer instances to send

        :return: None
        """
        for p in pointers:
            self.send_pointer(p)
