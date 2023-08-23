from unittest import mock

from django.contrib.messages import constants
from django.contrib.messages.storage import base
from django.contrib.messages.storage.base import Message
from django.test import SimpleTestCase, override_settings


class MessageTests(SimpleTestCase):
    def test_eq(self):
        msg_1 = Message(constants.INFO, "Test message 1")
        msg_2 = Message(constants.INFO, "Test message 2")
        msg_3 = Message(constants.WARNING, "Test message 1")
        self.assertEqual(msg_1, msg_1)
        self.assertEqual(msg_1, mock.ANY)
        self.assertNotEqual(msg_1, msg_2)
        self.assertNotEqual(msg_1, msg_3)
        self.assertNotEqual(msg_2, msg_3)

    @override_settings(
        MESSAGE_TAGS={
            constants.WARNING: "caution",
            constants.ERROR: "",
            12: "custom",
        }
    )
    def test_repr(self):
        tests = [
            (constants.INFO, "thing", "", "Message(level=20, message='thing')"),
            (
                constants.WARNING,
                "careful",
                "tag1 tag2",
                "Message(level=30, message='careful', extra_tags='tag1 tag2')",
            ),
            (
                constants.ERROR,
                "oops",
                "tag",
                "Message(level=40, message='oops', extra_tags='tag')",
            ),
            (12, "custom", "", "Message(level=12, message='custom')"),
        ]
        for level, message, extra_tags, expected in tests:
            with self.subTest(level=level, message=message):
                msg = Message(level, message, extra_tags=extra_tags)
                self.assertEqual(repr(msg), expected)


class TestLevelTags(SimpleTestCase):
    message_tags = {
        constants.INFO: "info",
        constants.DEBUG: "",
        constants.WARNING: "",
        constants.ERROR: "bad",
        constants.SUCCESS: "",
        12: "custom",
    }

    @override_settings(MESSAGE_TAGS=message_tags)
    def test_override_settings_level_tags(self):
        self.assertEqual(base.LEVEL_TAGS, self.message_tags)
