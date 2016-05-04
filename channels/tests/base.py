from django.test.testcases import TestCase
from channels import DEFAULT_CHANNEL_LAYER
from channels.asgi import channel_layers, ChannelLayerWrapper
from channels.message import Message
from asgiref.inmemory import ChannelLayer as InMemoryChannelLayer


class ChannelTestCase(TestCase):
    """
    TestCase subclass that provides easy methods for testing channels using
    an in-memory backend to capture messages, and assertion methods to allow
    checking of what was sent.

    Inherits from TestCase, so provides per-test transactions as long as the
    database backend supports it.
    """

    # Customizable so users can test multi-layer setups
    test_channel_aliases = [DEFAULT_CHANNEL_LAYER]

    def setUp(self):
        """
        Initialises in memory channel layer for the duration of the test
        """
        super(ChannelTestCase, self).setUp()
        self._old_layers = {}
        for alias in self.test_channel_aliases:
            # Swap in an in memory layer wrapper and keep the old one around
            self._old_layers[alias] = channel_layers.set(
                alias,
                ChannelLayerWrapper(
                    InMemoryChannelLayer(),
                    alias,
                    channel_layers[alias].routing,
                )
            )

    def tearDown(self):
        """
        Undoes the channel rerouting
        """
        for alias in self.test_channel_aliases:
            # Swap in an in memory layer wrapper and keep the old one around
            channel_layers.set(alias, self._old_layers[alias])
        del self._old_layers
        super(ChannelTestCase, self).tearDown()

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
