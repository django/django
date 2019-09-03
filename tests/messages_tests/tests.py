from unittest import mock

from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.test import SimpleTestCase


class MessageTests(SimpleTestCase):
    def test_eq(self):
        msg_1 = Message(constants.INFO, 'Test message 1')
        msg_2 = Message(constants.INFO, 'Test message 2')
        msg_3 = Message(constants.WARNING, 'Test message 1')
        self.assertEqual(msg_1, msg_1)
        self.assertEqual(msg_1, mock.ANY)
        self.assertNotEqual(msg_1, msg_2)
        self.assertNotEqual(msg_1, msg_3)
        self.assertNotEqual(msg_2, msg_3)
