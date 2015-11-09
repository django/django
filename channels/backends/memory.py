import json
import time
from collections import deque

from .base import BaseChannelBackend

queues = {}
groups = {}
locks = set()


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
        queues.setdefault(channel, deque()).append((message, time.time() + self.expiry))

    def receive_many(self, channels):
        if not channels:
            raise ValueError("Cannot receive on empty channel list!")
        # Try to pop a message from each channel
        self._clean_expired()
        for channel in channels:
            try:
                # This doesn't clean up empty channels - OK for testing.
                # For later versions, have cleanup w/lock.
                return channel, queues[channel].popleft()[0]
            except (IndexError, KeyError):
                pass
        return None, None

    def _clean_expired(self):
        # Handle expired messages
        for channel, messages in queues.items():
            while len(messages) and messages[0][1] < time.time():
                messages.popleft()
        # Handle expired groups
        for group, channels in list(groups.items()):
            for channel, expiry in list(channels.items()):
                if expiry < (time.time() - 10):
                    try:
                        del groups[group][channel]
                    except KeyError:
                        # Another thread might have got there first
                        pass

    def group_add(self, group, channel, expiry=None):
        """
        Adds the channel to the named group for at least 'expiry'
        seconds (expiry defaults to message expiry if not provided).
        """
        groups.setdefault(group, {})[channel] = time.time() + (expiry or self.expiry)

    def group_discard(self, group, channel):
        """
        Removes the channel from the named group if it is in the group;
        does nothing otherwise (does not error)
        """
        try:
            del groups[group][channel]
        except KeyError:
            pass

    def group_channels(self, group):
        """
        Returns an iterable of all channels in the group.
        """
        self._clean_expired()
        return groups.get(group, {}).keys()

    def lock_channel(self, channel):
        """
        Attempts to get a lock on the named channel. Returns True if lock
        obtained, False if lock not obtained.
        """
        # Probably not perfect for race conditions, but close enough considering
        # it shouldn't be used.
        if channel not in locks:
            locks.add(channel)
            return True
        else:
            return False

    def unlock_channel(self, channel):
        """
        Unlocks the named channel. Always succeeds.
        """
        locks.discard(channel)

    def flush(self):
        global queues, groups, locks
        queues = {}
        groups = {}
        locks = set()
