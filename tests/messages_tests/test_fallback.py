import random

from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.fallback import CookieStorage, FallbackStorage
from django.test import SimpleTestCase
from django.utils.crypto import get_random_string

from .base import BaseTests
from .test_cookie import set_cookie_data, stored_cookie_messages_count
from .test_session import set_session_data, stored_session_messages_count


class FallbackTests(BaseTests, SimpleTestCase):
    storage_class = FallbackStorage

    def get_request(self):
        self.session = {}
        request = super().get_request()
        request.session = self.session
        return request

    def get_cookie_storage(self, storage):
        return storage.storages[-2]

    def get_session_storage(self, storage):
        return storage.storages[-1]

    def stored_cookie_messages_count(self, storage, response):
        return stored_cookie_messages_count(self.get_cookie_storage(storage), response)

    def stored_session_messages_count(self, storage, response):
        return stored_session_messages_count(self.get_session_storage(storage))

    def stored_messages_count(self, storage, response):
        """
        Return the storage totals from both cookie and session backends.
        """
        return self.stored_cookie_messages_count(
            storage, response
        ) + self.stored_session_messages_count(storage, response)

    def test_get(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        # Set initial cookie data.
        example_messages = [str(i) for i in range(5)]
        set_cookie_data(cookie_storage, example_messages)
        # Overwrite the _get method of the fallback storage to prove it is not
        # used (it would cause a TypeError: 'NoneType' object is not callable).
        self.get_session_storage(storage)._get = None
        self.assertEqual(list(storage), example_messages)

    def test_get_empty(self):
        request = self.get_request()
        storage = self.storage_class(request)
        # Overwrite the _get method of the fallback storage to prove it is not
        # used (it would cause a TypeError: 'NoneType' object is not callable).
        self.get_session_storage(storage)._get = None
        self.assertEqual(list(storage), [])

    def test_get_fallback(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        session_storage = self.get_session_storage(storage)

        # Set initial cookie and session data.
        example_messages = [str(i) for i in range(5)]
        set_cookie_data(
            cookie_storage, example_messages[:4] + [CookieStorage.not_finished]
        )
        set_session_data(session_storage, example_messages[4:])
        self.assertEqual(list(storage), example_messages)

    def test_get_fallback_only(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        session_storage = self.get_session_storage(storage)
        # Set initial cookie and session data.
        example_messages = [str(i) for i in range(5)]
        set_cookie_data(cookie_storage, [CookieStorage.not_finished], encode_empty=True)
        set_session_data(session_storage, example_messages)
        self.assertEqual(list(storage), example_messages)

    def test_flush_used_backends(self):
        request = self.get_request()
        storage = self.storage_class(request)
        cookie_storage = self.get_cookie_storage(storage)
        session_storage = self.get_session_storage(storage)
        # Set initial cookie and session data.
        set_cookie_data(
            cookie_storage,
            [Message(constants.INFO, "cookie"), CookieStorage.not_finished],
        )
        set_session_data(session_storage, [Message(constants.INFO, "session")])
        # When updating, previously used but no longer needed backends are
        # flushed.
        response = self.get_response()
        list(storage)
        storage.update(response)
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 0)

    def test_no_fallback(self):
        """
        (1) A short number of messages whose data size doesn't exceed what is
        allowed in a cookie will all be stored in the CookieBackend.

        (2) If the CookieBackend can store all messages, the SessionBackend
        won't be written to at all.
        """
        storage = self.get_storage()
        response = self.get_response()
        # Overwrite the _store method of the fallback storage to prove it isn't
        # used (it would cause a TypeError: 'NoneType' object is not callable).
        self.get_session_storage(storage)._store = None
        for i in range(5):
            storage.add(constants.INFO, str(i) * 100)
        storage.update(response)
        cookie_storing = self.stored_cookie_messages_count(storage, response)
        self.assertEqual(cookie_storing, 5)
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 0)

    def test_session_fallback(self):
        """
        If the data exceeds what is allowed in a cookie, messages which did
        not fit are stored in the SessionBackend.
        """
        storage = self.get_storage()
        response = self.get_response()
        # see comment in CookieTests.test_cookie_max_length()
        msg_size = int((CookieStorage.max_cookie_size - 54) / 4.5 - 37)
        # Generate the same (tested) content every time that does not get run
        # through zlib compression.
        random.seed(42)
        for i in range(5):
            storage.add(constants.INFO, get_random_string(msg_size))
        storage.update(response)
        cookie_storing = self.stored_cookie_messages_count(storage, response)
        self.assertEqual(cookie_storing, 4)
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 1)

    def test_session_fallback_only(self):
        """
        Large messages, none of which fit in a cookie, are stored in the
        SessionBackend (and nothing is stored in the CookieBackend).
        """
        storage = self.get_storage()
        response = self.get_response()
        # Generate the same (tested) content every time that does not get run
        # through zlib compression.
        random.seed(42)
        storage.add(constants.INFO, get_random_string(5000))
        storage.update(response)
        cookie_storing = self.stored_cookie_messages_count(storage, response)
        self.assertEqual(cookie_storing, 0)
        session_storing = self.stored_session_messages_count(storage, response)
        self.assertEqual(session_storing, 1)
