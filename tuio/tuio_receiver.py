import argparse
import time
import multiprocessing

from typing import Dict
from pythonosc import dispatcher
from pythonosc import osc_server
from core.tuio.tuio_elements import TuioImagePattern, TuioBounds, TuioSymbol, TuioPointer, TuioData
from core.tuio.osc_receiver import OscReceiver


def bnd_handler(path, fixed_args, s_id, u_id, x_pos, y_pos, angle, width, height):
    """
    Static message handler for tuio 2.0 bnd messages. All extracted TuioBounds will be added to message queue in
    fixed_args.

    :param path: unused path (should be /tuio2/bnd)

    :param fixed_args: fixed arguments (fixed_args[0] should be message queue)

    :param s_id: session id

    :param u_id: user id

    :param x_pos: x position

    :param y_pos: y position

    :param angle: rotation angle

    :param width: width

    :param height: height

    :return: None
    """
    msg_queue = fixed_args[0]
    bnd = TuioBounds(
        x_pos=x_pos, y_pos=y_pos,
        angle=angle, width=width, height=height
    )
    msg_queue.put({"s_id": s_id, "u_id": u_id, "bnd": bnd})


def sym_handler(path, fixed_args, s_id, u_id, tu_id, c_id, sym_type, sym_value):
    """
    Static message handler for tuio 2.0 sym messages. All extracted TuioSymbol will be added to message queue in
    fixed_args.

    :param path: unused path (should be /tuio2/bnd)

    :param fixed_args: fixed arguments (fixed_args[0] should be message queue)

    :param s_id: session id

    :param u_id: user id

    :param tu_id: type id

    :param c_id: component id

    :param sym_type: symbol identifier type e.g. uuid

    :param sym_value: symbol identifier value

    :return: None
    """
    if sym_type != "uuid":
        raise ValueError("FAILURE: sym_type must be 'uuid'\n  > got:", sym_type)
    msg_queue = fixed_args[0]
    sym = TuioSymbol(uuid=sym_value, tu_id=tu_id, c_id=c_id)
    msg_queue.put({"s_id": s_id, "u_id": u_id, "sym": sym})


def ptr_handler(path, fixed_args, s_id, u_id, tu_id, c_id, x_pos, y_pos, angle, shear, radius, press):
    """
    Static message handler for tuio 2.0 ptr messages. All extracted TuioPointer will be added to message queue in
    fixed_args.

    :param path: unused path (should be /tuio2/bnd)

    :param fixed_args: fixed arguments (fixed_args[0] should be message queue)

    :param s_id: session id

    :param u_id: user id

    :param tu_id: type id

    :param c_id: component id

    :param x_pos: x position

    :param y_pos: y position

    :param angle: rotation angle

    :param shear: shear factor

    :param radius: radius

    :param press: press state (bool)

    :return: None
    """
    msg_queue = fixed_args[0]
    ptr = TuioPointer(
        s_id=s_id, u_id=u_id, tu_id=tu_id, c_id=c_id,
        x_pos=x_pos, y_pos=y_pos, angle=angle,
        shear=shear, radius=radius, press=bool(press)
    )
    msg_queue.put({"s_id": s_id, "u_id": u_id, "c_id": c_id, "ptr": ptr})


def dat_handler(path, fixed_args, s_id, u_id, c_id, mime_type, data):
    """
    Static message handler for tuio 2.0 dat messages. All extracted TuioData will be added to message queue in
    fixed_args.

    :param path: unused path (should be /tuio2/bnd)

    :param fixed_args: fixed arguments (fixed_args[0] should be message queue)

    :param s_id: session id

    :param u_id: user id

    :param c_id: component id

    :param mime_type: mime type of data

    :param data: data of mime type

    :return: None
    """
    msg_queue = fixed_args[0]
    dat = TuioData(mime_type=mime_type, data=data)
    msg_queue.put({"s_id": s_id, "u_id": u_id, "c_id": c_id, "dat": dat})


class TuioDispatcher(dispatcher.Dispatcher):
    """
    Extends pythonosc.dispatcher.Dispatcher mapping handlers for the following paths:
      - /tuio2/bnd, /tuio2/sym, /tuio2/ptr, /tuio2/dat
    Results of message handling will be written to respective message queue.
    """

    def __init__(self, bnd_queue=multiprocessing.Queue(), sym_queue=multiprocessing.Queue(), ptr_queue=multiprocessing.Queue(), dat_queue=multiprocessing.Queue()):
        """
        Constructor.
        :param bnd_queue: message queue TuioBounds are written to from /tuio2/bnd handler
        :param sym_queue: message queue TuioSymbol are written to from /tuio2/sym handler
        :param ptr_queue: message queue TuioPointer are written to from /tuio2/ptr handler
        :param dat_queue: message queue TuioData are written to from /tuio2/dat handler
        """
        super().__init__()
        self.bnd_queue = bnd_queue
        self.sym_queue = sym_queue
        self.ptr_queue = ptr_queue
        self.dat_queue = dat_queue
        self.map("/tuio2/bnd", bnd_handler, self.bnd_queue)
        self.map("/tuio2/sym", sym_handler, self.sym_queue)
        self.map("/tuio2/ptr", ptr_handler, self.ptr_queue)
        self.map("/tuio2/dat", dat_handler, self.dat_queue)


class TuioReceiver(OscReceiver):
    """
    Extends OscReceiver (see tuio/osc_receiver.py), using TuioDispatcher to handle tuio 2.0 bnd, sym, ptr & dat
    messages. Elements received can be updated from dispatcher message queues on demand.
    """

    def __init__(self, ip, port, element_timeout=1.0):
        """
        Constructor.

        :param ip: ip the OSC server listens at

        :param port: port the OSC server listens at

        :param element_timeout: expiration time (seconds) for element updates. Elements exceeding this time will be
        removed.
        """
        self._dispatcher = TuioDispatcher()
        super().__init__(ip, port, self._dispatcher)
        self._patterns = {}
        self._pattern_update_times = {}
        self._pointers = {}
        self._pointer_update_times = {}
        self._element_timeout = element_timeout

    def update_elements(self):
        """
        Updates all patterns given the unprocessed messages stored by the dispatcher. Returns an update log, listing all
        updated sym, bnd, ptr & dat element keys changed that way.

        :return: dict ({"bnd": [k1,...,kX], "sym": [k1, ..., kY], "ptr": [k1, ..., kZ], "dat": [k1, ..., kN]})
        """
        update_log = {"bnd": [], "sym": [], "ptr": [], "dat": []}
        time_now = time.time()
        # extract bnd updates
        self._process_bnd_updates(update_log, time_now)
        # extract sym updates
        self._process_sym_updates(update_log, time_now)
        # extract ptr updates
        self._process_ptr_updates(update_log, time_now)
        # extract dat updates
        self._process_dat_updates(update_log, time_now)
        # remove expired elements
        self._remove_expired_elements(time_now)
        return update_log

    def _process_bnd_updates(self, update_log, timestamp):
        """
        Helper function for self.update_elements() processing pending messages from the /tuio2/bnd handler.

        :param update_log: update log to be extended (as returned by self.update_elements)

        :param timestamp: time stamp for the update

        :return: None
        """
        while not self._dispatcher.bnd_queue.empty():
            bnd_msg = self._dispatcher.bnd_queue.get()
            s_id = bnd_msg["s_id"]
            u_id = bnd_msg["u_id"]
            key = TuioImagePattern.calc_key(s_id, u_id)
            if key not in self._patterns.keys():
                self._patterns[key] = TuioImagePattern(s_id=s_id, u_id=u_id)
            self._patterns[key].set_bnd(bnd_msg["bnd"])
            self._pattern_update_times[key] = timestamp
            if key not in update_log["bnd"]:
                update_log["bnd"].append(key)

    def _process_sym_updates(self, update_log, timestamp):
        """
        Helper function for self.update_elements() processing pending messages from the /tuio2/sym handler.

        :param update_log: update log to be extended (as returned by self.update_elements)

        :param timestamp: time stamp for the update

        :return: None
        """
        while not self._dispatcher.sym_queue.empty():
            sym_msg = self._dispatcher.sym_queue.get()
            s_id = sym_msg["s_id"]
            u_id = sym_msg["u_id"]
            key = TuioImagePattern.calc_key(s_id, u_id)
            if key not in self._patterns.keys():
                self._patterns[key] = TuioImagePattern(s_id=s_id, u_id=u_id)
                self._pattern_update_times[key] = timestamp
            if self._patterns[key].get_sym() != sym_msg["sym"]:
                self._patterns[key].set_sym(sym_msg["sym"])
                self._pattern_update_times[key] = timestamp
                if key not in update_log["sym"]:
                    update_log["sym"].append(key)

    def _process_ptr_updates(self, update_log, timestamp):
        """
        Helper function for self.update_elements() processing pending messages from the /tuio2/ptr handler.

        :param update_log: update log to be extended (as returned by self.update_elements)

        :param timestamp: time stamp for the update

        :return: None
        """
        while not self._dispatcher.ptr_queue.empty():
            ptr_msg = self._dispatcher.ptr_queue.get()
            ptr = ptr_msg["ptr"]
            key = ptr.key()
            prev_ptr = None
            if key in self._pointers:
                prev_ptr = self._pointers[key]
            self._pointers[key] = ptr
            self._pointer_update_times[key] = timestamp
            if prev_ptr is not None:
                self._pointers[key].append_data_list(prev_ptr.get_data())
            if key not in update_log["ptr"]:
                update_log["ptr"].append(key)

    def _process_dat_updates(self, update_log, timestamp):
        """
        Helper function for self.update_elements() processing pending messages from the /tuio2/dat handler.

        :param update_log: update log to be extended (as returned by self.update_elements)

        :param timestamp: time stamp for the update

        :return: None
        """
        while not self._dispatcher.dat_queue.empty():
            dat_msg = self._dispatcher.dat_queue.get()
            dat = dat_msg["dat"]
            key = TuioPointer.calc_key(dat_msg["s_id"],dat_msg["u_id"], dat_msg["c_id"])
            if key in self._pointers:
                self._pointers[key].append_data(dat, remove_similar=True)
                self._pointer_update_times[key] = timestamp
                update_log["dat"].append(key)

    def _remove_expired_elements(self, timestamp):
        """
        Helper function for self.update_elements() removing all expired elements which have exceeded a fixed time
        threshold since their last update.

        :param update_log: update log to be extended (as returned by self.update_elements)

        :param timestamp: time stamp for the update

        :return: None
        """
        if self._element_timeout > 0.0:
            pattern_keys = [key for key in self._patterns.keys()]
            for key in pattern_keys:
                last_updated = self._pattern_update_times[key]
                if timestamp - last_updated > self._element_timeout:
                    del self._patterns[key]
                    del self._pattern_update_times[key]
            pointer_keys = [k for k in self._pointers.keys()]
            for k in pointer_keys:
                last_updated = self._pointer_update_times[k]
                if timestamp - last_updated > self._element_timeout:
                    del self._pointers[k]
                    del self._pointer_update_times[k]

    def get_pattern(self, key) -> TuioImagePattern:
        """
        Getter for TuioImagePattern referenced by given key.

        :param key: string key identifying pattern.

        :return: TuioImagePattern
        """
        return self._patterns[key]

    def get_patterns(self, keys=[]) -> Dict[str, TuioImagePattern]:
        """
        Returns a dict of all TuioImagePatterns identified by key list.

        :param keys: keys to search for in dict of patterns maintained by this instance.

        :return: dict
        """
        if len(keys) == 0:
            return self._patterns
        return {key: self.get_pattern(key) for key in keys}

    def get_pointer(self, key) -> TuioPointer:
        """
        Getter for TuioPointer referenced by given key.

        :param key: string key identifying pointer.

        :return: TuioPointer
        """
        return self._pointers[key]

    def get_pointers(self, keys=[]) -> Dict[str, TuioPointer]:
        """
        Returns a dict of all TuioPointer identified by key list.

        :param keys: keys to search for in dict of pointers maintained by this instance.

        :return: dict
        """
        if len(keys) == 0:
            return self._pointers
        return {key: self.get_pointer(key) for key in keys}
