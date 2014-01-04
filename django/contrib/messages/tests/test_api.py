from django.test import TestCase, RequestFactory

from django.contrib import messages


class DummyStorage(object):
    """
    dummy message-store to test the api methods
    """

    def __init__(self):
        self.store = []

    def add(self, level, message, extra_tags=''):
        self.store.append(message)


class ApiTest(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.request = self.rf.request()
        self.storage = DummyStorage()

    def test_ok(self):
        msg = 'some message'

        self.request._messages = self.storage
        messages.add_message(self.request, messages.DEBUG, msg)
        self.assertIn(msg, self.storage.store)

    def test_request_is_none(self):
        msg = 'some message'

        self.request._messages = self.storage

        with self.assertRaises(TypeError):
            messages.add_message(None, messages.DEBUG, msg)

        self.assertEqual([], self.storage.store)

    def test_middleware_missing(self):
        msg = 'some message'

        with self.assertRaises(messages.MessageFailure):
            messages.add_message(self.request, messages.DEBUG, msg)

        self.assertEqual([], self.storage.store)

    def test_middleware_missing_silently(self):
        msg = 'some message'

        messages.add_message(self.request, messages.DEBUG, msg,
                             fail_silently=True)

        self.assertEqual([], self.storage.store)
