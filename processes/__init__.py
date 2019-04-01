import subprocess


class ProcessWrapper(object):
    """
    BC for all process based classes. Wraps subprocess.Popen(...) call, to instantiate a concurrent process.
    """

    def __init__(self):
        """
        Constructor.
        """
        self._running = False
        self._subprocess = None
        self._process_args = []
        self.return_code = None

    def _set_process_args(self, args=[]):
        """
        Sets the subprocess.Popen(args) values for 'args'. args[0] determines the program to call, while remainder of
        list are optional cmd parameters. Call start(), to trigger subprocess instantiation.

        :param args: list arguments in subprocess.Popen(args)

        :return: None
        """
        if not self._running:
            self._process_args = args

    def cleanup(self):
        """
        Override in derived classes to defined pre __del__ cleanup steps.

        :return: None
        """
        pass

    def start(self):
        """
        Starts configured process. (See also self._set_process_args(...), self.stop())

        :return: process ID assigned by system.
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
        Stops the running process. (See also self._set_process_args(...), self.stop())

        :return: None
        """
        if not self._running:
            return
        self._subprocess.terminate()
        self.return_code = self._subprocess.wait()
        self._running = False

    def is_running(self):
        """
        Returns true if the process is currently running.

        :return: bool
        """
        return self._running

    def wait(self):
        """
        Blocks until the running process is done.

        :return: process exit code.
        """
        return self._subprocess.wait()