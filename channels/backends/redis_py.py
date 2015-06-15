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

    def __init__(self, expiry=60, host="localhost", port=6379, prefix="django-channels:"):
        super(RedisChannelBackend, self).__init__(expiry)
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
        # Write out message into expiring key (avoids big items in list)
        key = uuid.uuid4()
        self.connection.set(
            key,
            json.dumps(message),
            ex = self.expiry + 10,
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
                return result[0][len(self.prefix):], json.loads(content)
            else:
                return None, None

    def __str__(self):
        return "%s(host=%s, port=%s)" % (self.__class__.__name__, self.host, self.port)
