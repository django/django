import time
import json
import datetime
import math
import redis
import random
import binascii
import uuid

from django.utils import six

from .base import BaseChannelBackend


class RedisChannelBackend(BaseChannelBackend):
    """
    ORM-backed channel environment. For development use only; it will span
    multiple processes fine, but it's going to be pretty bad at throughput.
    """

    def __init__(self, routing, expiry=60, hosts=None, prefix="django-channels:"):
        super(RedisChannelBackend, self).__init__(routing=routing, expiry=expiry)
        # Make sure they provided some hosts, or provide a default
        if not hosts:
            hosts = [("localhost", 6379)]
        for host, port in hosts:
            assert isinstance(host, six.string_types)
            assert int(port)
        self.hosts = hosts
        self.prefix = prefix
        # Precalculate some values for ring selection
        self.ring_size = len(self.hosts)
        self.ring_divisor = int(math.ceil(4096 / float(self.ring_size)))

    def consistent_hash(self, value):
        """
        Maps the value to a node value between 0 and 4095
        using MD5, then down to one of the ring nodes.
        """
        bigval = binascii.crc32(value) & 0xffffffff
        return (bigval // 0x100000) // self.ring_divisor

    def random_index(self):
        return random.randint(0, len(self.hosts) - 1)

    def connection(self, index):
        """
        Returns the correct connection for the current thread.

        Pass key to use a server based on consistent hashing of the key value;
        pass None to use a random server instead.
        """
        # If index is explicitly None, pick a random server
        if index is None:
            index = self.random_index()
        # Catch bad indexes
        if not (0 <= index < self.ring_size):
            raise ValueError("There are only %s hosts - you asked for %s!" % (self.ring_size, index))
        host, port = self.hosts[index]
        return redis.Redis(host=host, port=port)

    @property
    def connections(self):
        for i in range(len(self.hosts)):
            return self.connection(i)

    def send(self, channel, message):
        # if channel is no str (=> bytes) convert it
        if not isinstance(channel, str):
            channel = channel.decode('utf-8')
        # Pick a connection to the right server - consistent for response
        # channels, random for normal channels
        if channel.startswith("!"):
            index = self.consistent_hash(key)
            connection = self.connection(index)
        else:
            connection = self.connection(None)
        # Write out message into expiring key (avoids big items in list)
        # TODO: Use extended set, drop support for older redis?
        key = self.prefix + uuid.uuid4().get_hex()
        connection.set(
            key,
            json.dumps(message),
        )
        connection.expire(
            key,
            self.expiry + 10,
        )
        # Add key to list
        connection.rpush(
            self.prefix + channel,
            key,
        )
        # Set list to expire when message does (any later messages will bump this)
        connection.expire(
            self.prefix + channel,
            self.expiry + 10,
        )
        # TODO: Prune expired messages from same list (in case nobody consumes)

    def receive_many(self, channels):
        if not channels:
            raise ValueError("Cannot receive on empty channel list!")
        # Work out what servers to listen on for the given channels
        indexes = {}
        random_index = self.random_index()
        for channel in channels:
            if channel.startswith("!"):
                indexes.setdefault(self.consistent_hash(channel), []).append(channel)
            else:
                indexes.setdefault(random_index, []).append(channel)
        # Get a message from one of our channels
        while True:
            # Select a random connection to use
            # TODO: Would we be better trying to do this truly async?
            index = random.choice(indexes.keys())
            connection = self.connection(index)
            channels = indexes[index]
            # Shuffle channels to avoid the first ones starving others of workers
            random.shuffle(channels)
            # Pop off any waiting message
            result = connection.blpop([self.prefix + channel for channel in channels], timeout=1)
            if result:
                content = connection.get(result[1])
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
        self.connection(self.consistent_hash(group)).zadd(
            key,
            **{channel: time.time() + (expiry or self.expiry)}
        )

    def group_discard(self, group, channel):
        """
        Removes the channel from the named group if it is in the group;
        does nothing otherwise (does not error)
        """
        key = "%s:group:%s" % (self.prefix, group)
        self.connection(self.consistent_hash(group)).zrem(
            key,
            channel,
        )

    def group_channels(self, group):
        """
        Returns an iterable of all channels in the group.
        """
        key = "%s:group:%s" % (self.prefix, group)
        connection = self.connection(self.consistent_hash(group))
        # Discard old channels
        connection.zremrangebyscore(key, 0, int(time.time()) - 10)
        # Return current lot
        return connection.zrange(
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
        return bool(self.connection(self.consistent_hash(channel)).setnx(key, "1"))

    def unlock_channel(self, channel):
        """
        Unlocks the named channel. Always succeeds.
        """
        key = "%s:lock:%s" % (self.prefix, channel)
        self.connection(self.consistent_hash(channel)).delete(key)

    def __str__(self):
        return "%s(host=%s, port=%s)" % (self.__class__.__name__, self.host, self.port)
