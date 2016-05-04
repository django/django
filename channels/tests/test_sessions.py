from __future__ import unicode_literals

from django.conf import settings
from django.test import override_settings
from channels.exceptions import ConsumeLater
from channels.message import Message
from channels.sessions import channel_session, http_session, enforce_ordering, session_for_reply_channel
from channels.tests import ChannelTestCase


@override_settings(SESSION_ENGINE="django.contrib.sessions.backends.cache")
class SessionTests(ChannelTestCase):
    """
    Tests the channels session module.
    """

    def test_session_for_reply_channel(self):
        """
        Tests storing and retrieving values by reply_channel.
        """
        session1 = session_for_reply_channel("test-reply-channel")
        session1["testvalue"] = 42
        session1.save(must_create=True)
        session2 = session_for_reply_channel("test-reply-channel")
        self.assertEqual(session2["testvalue"], 42)

    def test_channel_session(self):
        """
        Tests the channel_session decorator
        """
        # Construct message to send
        message = Message({"reply_channel": "test-reply"}, None, None)
        # Run through a simple fake consumer that assigns to it
        @channel_session
        def inner(message):
            message.channel_session["num_ponies"] = -1
        inner(message)
        # Test the session worked
        session2 = session_for_reply_channel("test-reply")
        self.assertEqual(session2["num_ponies"], -1)

    def test_channel_session_double(self):
        """
        Tests the channel_session decorator detects being wrapped in itself
        and doesn't blow up.
        """
        # Construct message to send
        message = Message({"reply_channel": "test-reply"}, None, None)
        # Run through a simple fake consumer that should trigger the error
        @channel_session
        @channel_session
        def inner(message):
            message.channel_session["num_ponies"] = -1
        inner(message)
        # Test the session worked
        session2 = session_for_reply_channel("test-reply")
        self.assertEqual(session2["num_ponies"], -1)

    def test_channel_session_no_reply(self):
        """
        Tests the channel_session decorator detects no reply channel
        """
        # Construct message to send
        message = Message({}, None, None)
        # Run through a simple fake consumer that should trigger the error
        @channel_session
        @channel_session
        def inner(message):
            message.channel_session["num_ponies"] = -1
        with self.assertRaises(ValueError):
            inner(message)

    def test_http_session(self):
        """
        Tests that http_session correctly extracts a session cookie.
        """
        # Make a session to try against
        session1 = session_for_reply_channel("test-reply")
        # Construct message to send
        message = Message({
            "reply_channel": "test-reply",
            "http_version": "1.1",
            "method": "GET",
            "path": "/test2/",
            "headers": {
                "host": b"example.com",
                "cookie": ("%s=%s" % (settings.SESSION_COOKIE_NAME, session1.session_key)).encode("ascii"),
            },
        }, None, None)
        # Run it through http_session, make sure it works (test double here too)
        @http_session
        @http_session
        def inner(message):
            message.http_session["species"] = "horse"
        inner(message)
        # Check value assignment stuck
        session2 = session_for_reply_channel("test-reply")
        self.assertEqual(session2["species"], "horse")

    def test_enforce_ordering_slight(self):
        """
        Tests that slight mode of enforce_ordering works
        """
        # Construct messages to send
        message0 = Message({"reply_channel": "test-reply-a", "order": 0}, None, None)
        message1 = Message({"reply_channel": "test-reply-a", "order": 1}, None, None)
        message2 = Message({"reply_channel": "test-reply-a", "order": 2}, None, None)
        # Run them in an acceptable slight order
        @enforce_ordering(slight=True)
        def inner(message):
            pass
        inner(message0)
        inner(message2)
        inner(message1)

    def test_enforce_ordering_slight_fail(self):
        """
        Tests that slight mode of enforce_ordering fails on bad ordering
        """
        # Construct messages to send
        message2 = Message({"reply_channel": "test-reply-e", "order": 2}, None, None)
        # Run them in an acceptable strict order
        @enforce_ordering(slight=True)
        def inner(message):
            pass
        with self.assertRaises(ConsumeLater):
            inner(message2)

    def test_enforce_ordering_strict(self):
        """
        Tests that strict mode of enforce_ordering works
        """
        # Construct messages to send
        message0 = Message({"reply_channel": "test-reply-b", "order": 0}, None, None)
        message1 = Message({"reply_channel": "test-reply-b", "order": 1}, None, None)
        message2 = Message({"reply_channel": "test-reply-b", "order": 2}, None, None)
        # Run them in an acceptable strict order
        @enforce_ordering
        def inner(message):
            pass
        inner(message0)
        inner(message1)
        inner(message2)

    def test_enforce_ordering_strict_fail(self):
        """
        Tests that strict mode of enforce_ordering fails on bad ordering
        """
        # Construct messages to send
        message0 = Message({"reply_channel": "test-reply-c", "order": 0}, None, None)
        message2 = Message({"reply_channel": "test-reply-c", "order": 2}, None, None)
        # Run them in an acceptable strict order
        @enforce_ordering
        def inner(message):
            pass
        inner(message0)
        with self.assertRaises(ConsumeLater):
            inner(message2)

    def test_enforce_ordering_fail_no_order(self):
        """
        Makes sure messages with no "order" key fail
        """
        message0 = Message({"reply_channel": "test-reply-d"}, None, None)
        @enforce_ordering(slight=True)
        def inner(message):
            pass
        with self.assertRaises(ValueError):
            inner(message0)
