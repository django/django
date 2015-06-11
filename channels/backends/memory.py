import time
import json
from collections import deque
from .base import BaseChannelBackend

queues = {}

class InMemoryChannelBackend(BaseChannelBackend):
    """
    In-memory channel implementation. Intended only for use with threading,
    in low-throughput development environments.
    """

    local_only = True

    def send(self, channel, message):
        # Try JSON encoding it to make sure it would, but store the native version
        json.dumps(message)
        # Add to the deque, making it if needs be
        queues.setdefault(channel, deque()).append(message)

    def receive_many(self, channels):
        if not channels:
            raise ValueError("Cannot receive on empty channel list!")
        # Try to pop a message from each channel
        for channel in channels:
            try:
                # This doesn't clean up empty channels - OK for testing.
                # For later versions, have cleanup w/lock.
                return channel, queues[channel].popleft()
            except (IndexError, KeyError):
                pass
        return None, None

