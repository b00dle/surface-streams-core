import subprocess


class ProcessWrapper(object):
    """
    BC for all process based classes.
    """

    def __init__(self):
        self._running = False
        self._subprocess = None
        self._process_args = []
        self.return_code = None

    def _set_process_args(self, args=[]):
        """
        Sets the subprocess.Popen(args) values for 'args'.
        args[0] determines the program to call, while remainder of list are
        optional cmd parameters. Call start(), to trigger subprocess instantiation.
        :param popen_list: list arguments in subprocess.Popen(args)
        :return:
        """
        if not self._running:
            self._process_args = args

    def cleanup(self):
        pass

    def start(self):
        """
        Starts subprocess with process_args set.
        See also: _set_process_args, stop
        :return: process ID
        """
        if self._running or len(self._process_args) == 0:
            return
        cmd_str = ""
        for arg in self._process_args:
            cmd_str += " " + arg
        print("Running:", cmd_str)
        self._subprocess = subprocess.Popen(self._process_args)
        print("  > PID", self._subprocess.pid)
        self._running = True
        return self._subprocess.pid

    def stop(self):
        """
        Stops the subprocess if running.
        See also: _set_process_args, start
        :return:
        """
        if not self._running:
            return
        self._subprocess.terminate()
        self.return_code = self._subprocess.wait()
        self._running = False

    def is_running(self):
        return self._running

    def wait(self):
        return self._subprocess.wait()