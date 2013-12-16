from __future__ import division

import sched
import heapq
from collections import defaultdict, namedtuple
import threading
import time


class RequestScheduler(object):
    History = namedtuple('History', ('first_request', 'requests'))

    def __init__(self, ratio):
        """
        ratio: age * ratio = 1 request
        """
        self.request_history = defaultdict(
            lambda: self.History(time.time(), 0))
        self.ratio = ratio
        self._history_lock = threading.Lock()

    def pop(self):
        """Removes the item with the lowest priority
        >>> rq = RequestScheduler(0.5) # 2 seconds per request
        >>> rq.mark('foo')
        >>> rq.mark('bar')
        >>> rq.mark('foo')
        >>> rq._age = lambda _: 2.0
        >>> rq.pop()
        'foo'
        >>> "foo" in rq
        False
        """

        with self._history_lock:
            _, name = max((self.priority(v), k) for (k, v) in
                               self.request_history.items())
            del self.request_history[name]
            return name

    def priority(self, history):
        """requests + (ratio * age)

        >>> rq = RequestScheduler(0.5) # 2 seconds per request
        >>> rq._age = lambda _: 2.0
        >>> rq.priority(rq.History(None, 1))
        2.0
        >>> rq.priority(rq.History(None, 2))
        3.0
        """
        return  history.requests + (
            self._age(history.first_request) * self.ratio)

    def mark(self, name):
        """Mark name as having been requested."""
        with self._history_lock:
            event_time, priority = self.request_history[name]
            self.request_history[name] = self.History(event_time, priority+1)

    @staticmethod
    def _age(event_time):
        """calculate the age of a given time."""
        return time.time() - event_time

    def __contains__(self, value):
        return value in self.request_history


class InvalidatorScheduler(object):
    pass
