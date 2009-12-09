from django import http
from django.contrib.auth.models import User
from django.contrib.messages.storage.user_messages import UserMessagesStorage,\
    LegacyFallbackStorage
from django.contrib.messages.tests.cookie import set_cookie_data
from django.contrib.messages.tests.fallback import FallbackTest
from django.test import TestCase


class UserMessagesTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='tester')

    def test_add(self):
        storage = UserMessagesStorage(http.HttpRequest())
        self.assertRaises(NotImplementedError, storage.add, 'Test message 1')

    def test_get_anonymous(self):
        # Ensure that the storage still works if no user is attached to the
        # request.
        storage = UserMessagesStorage(http.HttpRequest())
        self.assertEqual(len(storage), 0)

    def test_get(self):
        storage = UserMessagesStorage(http.HttpRequest())
        storage.request.user = self.user
        self.user.message_set.create(message='test message')

        self.assertEqual(len(storage), 1)
        self.assertEqual(list(storage)[0].message, 'test message')


class LegacyFallbackTest(FallbackTest, TestCase):
    storage_class = LegacyFallbackStorage

    def setUp(self):
        super(LegacyFallbackTest, self).setUp()
        self.user = User.objects.create(username='tester')

    def get_request(self, *args, **kwargs):
        request = super(LegacyFallbackTest, self).get_request(*args, **kwargs)
        request.user = self.user
        return request

    def test_get_legacy_only(self):
        request = self.get_request()
        storage = self.storage_class(request)
        self.user.message_set.create(message='user message')

        # Test that the message actually contains what we expect.
        self.assertEqual(len(storage), 1)
        self.assertEqual(list(storage)[0].message, 'user message')

    def test_get_legacy(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        self.user.message_set.create(message='user message')
        set_cookie_data(cookie_storage, ['cookie'])

        # Test that the message actually contains what we expect.
        self.assertEqual(len(storage), 2)
        self.assertEqual(list(storage)[0].message, 'user message')
        self.assertEqual(list(storage)[1], 'cookie')
