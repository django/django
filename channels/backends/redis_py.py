import time
import json
import datetime
import redis
import uuid

from .base import BaseChannelBackend


class RedisChannelBackend(BaseChannelBackend):
    """
    ORM-backed channel environment. For development use only; it will span
    multiple processes fine, but it's going to be pretty bad at throughput.
    """

    def __init__(self, routing, expiry=60, host="localhost", port=6379, prefix="django-channels:"):
        super(RedisChannelBackend, self).__init__(routing=routing, expiry=expiry)
        self.host = host
        self.port = port
        self.prefix = prefix

    @property
    def connection(self):
        """
        Returns the correct connection for the current thread.
        """
        return redis.Redis(host=self.host, port=self.port)

    def send(self, channel, message):
        # if channel is no str (=> bytes) convert it
        if not isinstance(channel, str):
            channel = channel.decode('utf-8')

        # Write out message into expiring key (avoids big items in list)
        key = self.prefix + uuid.uuid4().get_hex()
        self.connection.set(
            key,
            json.dumps(message),
        )
        self.connection.expire(
            key,
            self.expiry + 10,
        )
        # Add key to list
        self.connection.rpush(
            self.prefix + channel,
            key,
        )
        # Set list to expire when message does (any later messages will bump this)
        self.connection.expire(
            self.prefix + channel,
            self.expiry + 10,
        )
        # TODO: Prune expired messages from same list (in case nobody consumes)

    def receive_many(self, channels):
        if not channels:
            raise ValueError("Cannot receive on empty channel list!")
        # Get a message from one of our channels
        while True:
            result = self.connection.blpop([self.prefix + channel for channel in channels], timeout=1)
            if result:
                content = self.connection.get(result[1])
                if content is None:
                    continue
                return result[0][len(self.prefix):].decode("utf-8"), json.loads(content.decode("utf-8"))
            else:
                return None, None

    def group_add(self, group, channel, expiry=None):
        """
        Adds the channel to the named group for at least 'expiry'
        seconds (expiry defaults to message expiry if not provided).
        """
        key = "%s:group:%s" % (self.prefix, group)
        self.connection.zadd(
            key,
            **{channel: time.time() + (expiry or self.expiry)}
        )

    def group_discard(self, group, channel):
        """
        Removes the channel from the named group if it is in the group;
        does nothing otherwise (does not error)
        """
        key = "%s:group:%s" % (self.prefix, group)
        self.connection.zrem(
            key,
            channel,
        )

    def group_channels(self, group):
        """
        Returns an iterable of all channels in the group.
        """
        key = "%s:group:%s" % (self.prefix, group)
        # Discard old channels
        self.connection.zremrangebyscore(key, 0, int(time.time()) - 10)
        # Return current lot
        return self.connection.zrange(
            key,
            0,
            -1,
        )

    # TODO: send_group efficient implementation using Lua

    def lock_channel(self, channel, expiry=None):
        """
        Attempts to get a lock on the named channel. Returns True if lock
        obtained, False if lock not obtained.
        """
        key = "%s:lock:%s" % (self.prefix, channel)
        return bool(self.connection.setnx(key, "1"))

    def unlock_channel(self, channel):
        """
        Unlocks the named channel. Always succeeds.
        """
        key = "%s:lock:%s" % (self.prefix, channel)
        self.connection.delete(key)

    def __str__(self):
        return "%s(host=%s, port=%s)" % (self.__class__.__name__, self.host, self.port)
