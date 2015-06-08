import time
import string
import random
from collections import deque
from .base import BaseChannelBackend

queues = {}

class InMemoryChannelBackend(BaseChannelBackend):
    """
    In-memory channel implementation. Intended only for use with threading,
    in low-throughput development environments.
    """

    def send(self, channel, message):
        # Add to the deque, making it if needs be
        queues.setdefault(channel, deque()).append(message)

    def receive_many(self, channels):
        while True:
            # Try to pop a message from each channel
            for channel in channels:
                try:
                    # This doesn't clean up empty channels - OK for testing.
                    # For later versions, have cleanup w/lock.
                    return channel, queues[channel].popleft()
                except (IndexError, KeyError):
                    pass
            # If all empty, sleep for a little bit
            time.sleep(0.01)

