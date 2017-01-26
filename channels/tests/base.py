from __future__ import unicode_literals

import copy
import random
import string
from functools import wraps

from asgiref.inmemory import ChannelLayer as InMemoryChannelLayer
from django.db import close_old_connections
from django.test.testcases import TestCase, TransactionTestCase

from .. import DEFAULT_CHANNEL_LAYER
from ..asgi import ChannelLayerWrapper, channel_layers
from ..channel import Group
from ..message import Message
from ..routing import Router, include
from ..signals import consumer_finished, consumer_started


class ChannelTestCaseMixin(object):
    """
    TestCase subclass that provides easy methods for testing channels using
    an in-memory backend to capture messages, and assertion methods to allow
    checking of what was sent.

    Inherits from TestCase, so provides per-test transactions as long as the
    database backend supports it.
    """

    # Customizable so users can test multi-layer setups
    test_channel_aliases = [DEFAULT_CHANNEL_LAYER]

    def _pre_setup(self):
        """
        Initialises in memory channel layer for the duration of the test
        """
        super(ChannelTestCaseMixin, self)._pre_setup()
        self._old_layers = {}
        for alias in self.test_channel_aliases:
            # Swap in an in memory layer wrapper and keep the old one around
            self._old_layers[alias] = channel_layers.set(
                alias,
                ChannelLayerWrapper(
                    InMemoryChannelLayer(),
                    alias,
                    channel_layers[alias].routing[:],
                )
            )

    def _post_teardown(self):
        """
        Undoes the channel rerouting
        """
        for alias in self.test_channel_aliases:
            # Swap in an in memory layer wrapper and keep the old one around
            channel_layers.set(alias, self._old_layers[alias])
        del self._old_layers
        super(ChannelTestCaseMixin, self)._post_teardown()

    def get_next_message(self, channel, alias=DEFAULT_CHANNEL_LAYER, require=False):
        """
        Gets the next message that was sent to the channel during the test,
        or None if no message is available.

        If require is true, will fail the test if no message is received.
        """
        recv_channel, content = channel_layers[alias].receive_many([channel])
        if recv_channel is None:
            if require:
                self.fail("Expected a message on channel %s, got none" % channel)
            else:
                return None
        return Message(content, recv_channel, channel_layers[alias])


class ChannelTestCase(ChannelTestCaseMixin, TestCase):
    pass


class TransactionChannelTestCase(ChannelTestCaseMixin, TransactionTestCase):
    pass


class Client(object):
    """
    Channel client abstraction that provides easy methods for testing full live cycle of message in channels
    with determined the reply channel
    """

    def __init__(self, alias=DEFAULT_CHANNEL_LAYER):
        self.reply_channel = alias + ''.join([random.choice(string.ascii_letters) for _ in range(5)])
        self.alias = alias

    @property
    def channel_layer(self):
        """Channel layer as lazy property"""
        return channel_layers[self.alias]

    def get_next_message(self, channel):
        """
        Gets the next message that was sent to the channel during the test,
        or None if no message is available.
        """
        recv_channel, content = channel_layers[self.alias].receive_many([channel])
        if recv_channel is None:
            return
        return Message(content, recv_channel, channel_layers[self.alias])

    def get_consumer_by_channel(self, channel):
        message = Message({'text': ''}, channel, self.channel_layer)
        match = self.channel_layer.router.match(message)
        if match:
            consumer, kwargs = match
            return consumer

    def send(self, to, content={}):
        """
        Send a message to a channel.
        Adds reply_channel name to the message.
        """
        content = copy.deepcopy(content)
        content.setdefault('reply_channel', self.reply_channel)
        self.channel_layer.send(to, content)

    def consume(self, channel, fail_on_none=True):
        """
        Get next message for channel name and run appointed consumer
        """
        message = self.get_next_message(channel)
        if message:
            match = self.channel_layer.router.match(message)
            if match:
                consumer, kwargs = match
                try:
                    consumer_started.send(sender=self.__class__)
                    return consumer(message, **kwargs)
                finally:
                    # Copy Django's workaround so we don't actually close DB conns
                    consumer_finished.disconnect(close_old_connections)
                    consumer_finished.send(sender=self.__class__)
                    consumer_finished.connect(close_old_connections)
            elif fail_on_none:
                raise AssertionError("Can't find consumer for message %s" % message)
        elif fail_on_none:
            raise AssertionError("No message for channel %s" % channel)

    def send_and_consume(self, channel, content={}, fail_on_none=True):
        """
        Reproduce full life cycle of the message
        """
        self.send(channel, content)
        return self.consume(channel, fail_on_none=fail_on_none)

    def receive(self):
        """
        Get content of next message for reply channel if message exists
        """
        message = self.get_next_message(self.reply_channel)
        if message:
            return message.content

    def join_group(self, group_name):
        Group(group_name).add(self.reply_channel)


class apply_routes(object):
    """
    Decorator/ContextManager for rewrite layers routes in context.
    Helpful for testing group routes/consumers as isolated application

    The applying routes can be list of instances of Route or list of this lists
    """

    def __init__(self, routes, aliases=[DEFAULT_CHANNEL_LAYER]):
        self._aliases = aliases
        self.routes = routes
        self._old_routing = {}

    def enter(self):
        """
        Store old routes and apply new one
        """
        for alias in self._aliases:
            channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
            self._old_routing[alias] = channel_layer.routing
            if isinstance(self.routes, (list, tuple)):
                if isinstance(self.routes[0], (list, tuple)):
                    routes = list(map(include, self.routes))
                else:
                    routes = self.routes
            else:
                routes = [self.routes]
            channel_layer.routing = routes
            channel_layer.router = Router(routes)

    def exit(self, exc_type=None, exc_val=None, exc_tb=None):
        """
        Undoes rerouting
        """
        for alias in self._aliases:
            channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
            channel_layer.routing = self._old_routing[alias]
            channel_layer.router = Router(self._old_routing[alias])

    __enter__ = enter
    __exit__ = exit

    def __call__(self, test_func):
        if isinstance(test_func, type):
            old_setup = test_func.setUp
            old_teardown = test_func.tearDown

            def new_setup(this):
                self.enter()
                old_setup(this)

            def new_teardown(this):
                self.exit()
                old_teardown(this)

            test_func.setUp = new_setup
            test_func.tearDown = new_teardown
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
            return inner
