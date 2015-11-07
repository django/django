from __future__ import unicode_literals

from django.test import TestCase
from ..backends.database import DatabaseChannelBackend
from ..backends.redis_py import RedisChannelBackend
from ..backends.memory import InMemoryChannelBackend


class MemoryBackendTests(TestCase):

    backend_class = InMemoryChannelBackend

    def setUp(self):
        self.backend = self.backend_class(routing={})
        self.backend.flush()

    def test_send_recv(self):
        """
        Tests that channels can send and receive messages.
        """
        self.backend.send("test", {"value": "blue"})
        self.backend.send("test", {"value": "green"})
        self.backend.send("test2", {"value": "red"})
        # Get just one first
        channel, message = self.backend.receive_many(["test"])
        self.assertEqual(channel, "test")
        self.assertEqual(message, {"value": "blue"})
        # And the second
        channel, message = self.backend.receive_many(["test"])
        self.assertEqual(channel, "test")
        self.assertEqual(message, {"value": "green"})
        # And the other channel with multi select
        channel, message = self.backend.receive_many(["test", "test2"])
        self.assertEqual(channel, "test2")
        self.assertEqual(message, {"value": "red"})

    def test_message_expiry(self):
        self.backend = self.backend_class(routing={}, expiry=-100)
        self.backend.send("test", {"value": "blue"})
        channel, message = self.backend.receive_many(["test"])
        self.assertIs(channel, None)
        self.assertIs(message, None)

    def test_groups(self):
        """
        Tests that group addition and removal and listing works
        """
        self.backend.group_add("tgroup", "test")
        self.backend.group_add("tgroup", "test2€")
        self.backend.group_add("tgroup2", "test3")
        self.assertEqual(
            set(self.backend.group_channels("tgroup")),
            {"test", "test2€"},
        )
        self.backend.group_discard("tgroup", "test2€")
        self.backend.group_discard("tgroup", "test2€")
        self.assertEqual(
            list(self.backend.group_channels("tgroup")),
            ["test"],
        )

    def test_group_send(self):
        """
        Tests sending to groups.
        """
        self.backend.group_add("tgroup", "test")
        self.backend.group_add("tgroup", "test2")
        self.backend.send_group("tgroup", {"value": "orange"})
        channel, message = self.backend.receive_many(["test"])
        self.assertEqual(channel, "test")
        self.assertEqual(message, {"value": "orange"})
        channel, message = self.backend.receive_many(["test2"])
        self.assertEqual(channel, "test2")
        self.assertEqual(message, {"value": "orange"})

    def test_group_expiry(self):
        self.backend = self.backend_class(routing={}, expiry=-100)
        self.backend.group_add("tgroup", "test")
        self.backend.group_add("tgroup", "test2")
        self.assertEqual(
            list(self.backend.group_channels("tgroup")),
            [],
        )


class RedisBackendTests(MemoryBackendTests):

    backend_class = RedisChannelBackend


class DatabaseBackendTests(MemoryBackendTests):

    backend_class = DatabaseChannelBackend
