import time
import string
import random
from collections import deque
from .base import BaseChannel

queues = {}
closed = set()

class InMemoryChannel(BaseChannel):
    """
    In-memory channel implementation. Intended only for use with threading,
    in low-throughput development environments.
    """

    def send(self, **kwargs):
        # Don't allow if closed
        if self.name in closed:
            raise Channel.ClosedError("%s is closed" % self.name)
        # Add to the deque, making it if needs be
        queues.setdefault(self.name, deque()).append(kwargs)

    @property
    def closed(self):
        # Check closed set
        return self.name in closed

    def close(self):
        # Add to closed set
        closed.add(self.name)

    @classmethod
    def receive_many(self, channel_names):
        while True:
            # Try to pop a message from each channel
            for channel_name in channel_names:
                try:
                    # This doesn't clean up empty channels - OK for testing.
                    # For later versions, have cleanup w/lock.
                    return channel_name, queues[channel_name].popleft()
                except (IndexError, KeyError):
                    pass
            # If all empty, sleep for a little bit
            time.sleep(0.01)

    @classmethod
    def new_name(self, prefix):
        return "%s.%s" % (prefix, "".join(random.choice(string.ascii_letters) for i in range(16)))
