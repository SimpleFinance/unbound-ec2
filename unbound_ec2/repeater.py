import threading


class RecursiveRepeater(threading.Thread):
    """Periodically runs code in a thread.
    """

    def __init__(self, delay, callme):
        """Calls `callme`  every  `delay` seconds.
        """
        threading.Thread.__init__(self)
        self.callme = callme
        self.delay = delay
        self.event = threading.Event()
        self.daemon = True

    def run(self):
        while not self.event.wait(1.0):
            self.callme()
            self.event.wait(self.delay)

    def stop(self):
        self.event.set()
        self.join()
