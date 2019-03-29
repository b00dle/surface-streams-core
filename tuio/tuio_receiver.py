import argparse
import time
import multiprocessing
from pythonosc import dispatcher
from pythonosc import osc_server
from tuio.tuio_elements import TuioImagePattern, TuioBounds, TuioSymbol, TuioPointer, TuioData
from typing import Dict


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


def bnd_handler(path, fixed_args, s_id, u_id, x_pos, y_pos, angle, width, height):
    msg_queue = fixed_args[0]
    bnd = TuioBounds(
        x_pos=x_pos, y_pos=y_pos,
        angle=angle, width=width, height=height
    )
    msg_queue.put({"s_id": s_id, "u_id": u_id, "bnd": bnd})


def sym_handler(path, fixed_args, s_id, u_id, tu_id, c_id, sym_type, sym_value):
    if sym_type != "uuid":
        raise ValueError("FAILURE: sym_type must be 'uuid'\n  > got:", sym_type)
    msg_queue = fixed_args[0]
    sym = TuioSymbol(uuid=sym_value, tu_id=tu_id, c_id=c_id)
    msg_queue.put({"s_id": s_id, "u_id": u_id, "sym": sym})


def ptr_handler(path, fixed_args, s_id, u_id, tu_id, c_id, x_pos, y_pos, angle, shear, radius, press):
    msg_queue = fixed_args[0]
    ptr = TuioPointer(
        s_id=s_id, u_id=u_id, tu_id=tu_id, c_id=c_id,
        x_pos=x_pos, y_pos=y_pos, angle=angle,
        shear=shear, radius=radius, press=bool(press)
    )
    msg_queue.put({"s_id": s_id, "u_id": u_id, "c_id": c_id, "ptr": ptr})


def dat_handler(path, fixed_args, s_id, u_id, c_id, mime_type, data):
    msg_queue = fixed_args[0]
    dat = TuioData(mime_type=mime_type, data=data)
    msg_queue.put({"s_id": s_id, "u_id": u_id, "c_id": c_id, "dat": dat})


class TuioDispatcher(dispatcher.Dispatcher):
    def __init__(self, bnd_queue=multiprocessing.Queue(), sym_queue=multiprocessing.Queue(), ptr_queue=multiprocessing.Queue(), dat_queue=multiprocessing.Queue()):
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
    # TODO: different key for patterns and pointers
    # s_id will not be unique as soon as we have different u_ids
    def __init__(self, ip, port, element_timeout=1.0):
        self._dispatcher = TuioDispatcher()
        super().__init__(ip, port, self._dispatcher)
        self._patterns = {}
        self._pattern_update_times = {}
        self._pointers = {}
        self._pointer_update_times = {}
        self._element_timeout = element_timeout

    def update_elements(self):
        """ Updates all patterns given the unprocessed messages
            stored by the dispatcher. Returns an update log,
            listing all updated_bnd s_ids and all
            updated_sim s_ids changed that way.
            Structure:
            update_log = {
                "bnd": [num1, ..., numX],
                "sym": [num1, ..., numY]
            }"""
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
        while not self._dispatcher.dat_queue.empty():
            dat_msg = self._dispatcher.dat_queue.get()
            dat = dat_msg["dat"]
            key = TuioPointer.calc_key(dat_msg["s_id"],dat_msg["u_id"], dat_msg["c_id"])
            if key in self._pointers:
                self._pointers[key].append_data(dat, remove_similar=True)
                self._pointer_update_times[key] = timestamp
                update_log["dat"].append(key)

    def _remove_expired_elements(self, timestamp):
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
        return self._patterns[key]

    def get_patterns(self, keys=[]) -> Dict[int, TuioImagePattern]:
        if len(keys) == 0:
            return self._patterns
        return {key: self.get_pattern(key) for key in keys}

    def get_pointer(self, key) -> TuioPointer:
        return self._pointers[key]

    def get_pointers(self, keys=[]) -> Dict[str, TuioPointer]:
        if len(keys) == 0:
            return self._pointers
        return {key: self.get_pointer(key) for key in keys}


def run_pattern_receiver(ip="0.0.0.0", port=5004):
    server = TuioReceiver(ip, port)
    server.start()

    while True:
        update_log = server.update_elements()

        nothing_updated = True
        if len(update_log["bnd"]) > 0:
            nothing_updated = False
            print("Received BND update\n  > ", server.get_patterns(update_log["bnd"]))
        if len(update_log["sym"]) > 0:
            nothing_updated = False
            print("Received SYM update\n  > ", server.get_patterns(update_log["sym"]))
        if len(update_log["ptr"]) > 0:
            nothing_updated = False
            print("Received PTR update\n  > ", server.get_pointers(update_log["ptr"]))
        if nothing_updated:
            print("Waiting for BND or SYM update")

        time.sleep(1)


'''
minimum example of osc receiver
'''


def _print_foo_handler(unused_addr, fixed_args, *lst):
    fixed_args[0].put([unused_addr, lst])


def _print_foo_handler_fixed(unused_addr, fixed_args, num, str, bool):
    fixed_args[0].put([unused_addr, num, str, bool])


def _print_foo_handler_mixed(unused_addr, fixed_args, num, *lst):
    fixed_args[0].put([unused_addr, num, lst])


def run(ip="127.0.0.1", port=5005):
    msg_queue = multiprocessing.Queue()

    osc_disp = dispatcher.Dispatcher()
    osc_disp.map("/foo", _print_foo_handler_mixed, msg_queue)

    server = osc_server.ThreadingOSCUDPServer((ip, port), osc_disp)
    print("Serving on {}".format(server.server_address))
    server_process = multiprocessing.Process(target=server.serve_forever)
    server_process.start()

    # this piece should be embedded into the frame by frame reconstruction on the client side
    while True:
        print("WAITING FOR MESSAGE")

        while not msg_queue.empty():
            print(msg_queue.get())

        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--ip",
        default="127.0.0.1",
        help="The ip to listen on")

    parser.add_argument(
        "--port",
        type=int,
        default=5005,
        help="The port to listen on"
    )

    args = parser.parse_args()

    run(args.ip, args.port)
