import json
import random
from unittest import TestCase

from django.conf import settings
from django.contrib.messages import Message, constants
from django.contrib.messages.storage.cookie import (
    CookieStorage,
    MessageDecoder,
    MessageEncoder,
    bisect_keep_left,
    bisect_keep_right,
)
from django.test import SimpleTestCase, override_settings
from django.utils.crypto import get_random_string
from django.utils.safestring import SafeData, mark_safe

from .base import BaseTests


def set_cookie_data(storage, messages, invalid=False, encode_empty=False):
    """
    Set ``request.COOKIES`` with the encoded data and remove the storage
    backend's loaded data cache.
    """
    encoded_data = storage._encode(messages, encode_empty=encode_empty)
    if invalid:
        # Truncate the first character so that the hash is invalid.
        encoded_data = encoded_data[1:]
    storage.request.COOKIES = {CookieStorage.cookie_name: encoded_data}
    if hasattr(storage, "_loaded_data"):
        del storage._loaded_data


def stored_cookie_messages_count(storage, response):
    """
    Return an integer containing the number of messages stored.
    """
    # Get a list of cookies, excluding ones with a max-age of 0 (because
    # they have been marked for deletion).
    cookie = response.cookies.get(storage.cookie_name)
    if not cookie or cookie["max-age"] == 0:
        return 0
    data = storage._decode(cookie.value)
    if not data:
        return 0
    if data[-1] == CookieStorage.not_finished:
        data.pop()
    return len(data)


@override_settings(
    SESSION_COOKIE_DOMAIN=".example.com",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
)
class CookieTests(BaseTests, SimpleTestCase):
    storage_class = CookieStorage

    def stored_messages_count(self, storage, response):
        return stored_cookie_messages_count(storage, response)

    def encode_decode(self, *args, **kwargs):
        storage = self.get_storage()
        message = [Message(constants.DEBUG, *args, **kwargs)]
        encoded = storage._encode(message)
        return storage._decode(encoded)[0]

    def test_get(self):
        storage = self.storage_class(self.get_request())
        # Set initial data.
        example_messages = ["test", "me"]
        set_cookie_data(storage, example_messages)
        # The message contains what's expected.
        self.assertEqual(list(storage), example_messages)

    @override_settings(SESSION_COOKIE_SAMESITE="Strict")
    def test_cookie_settings(self):
        """
        CookieStorage honors SESSION_COOKIE_DOMAIN, SESSION_COOKIE_SECURE, and
        SESSION_COOKIE_HTTPONLY (#15618, #20972).
        """
        # Test before the messages have been consumed
        storage = self.get_storage()
        response = self.get_response()
        storage.add(constants.INFO, "test")
        storage.update(response)
        messages = storage._decode(response.cookies["messages"].value)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, "test")
        self.assertEqual(response.cookies["messages"]["domain"], ".example.com")
        self.assertEqual(response.cookies["messages"]["expires"], "")
        self.assertIs(response.cookies["messages"]["secure"], True)
        self.assertIs(response.cookies["messages"]["httponly"], True)
        self.assertEqual(response.cookies["messages"]["samesite"], "Strict")

        # Deletion of the cookie (storing with an empty value) after the
        # messages have been consumed.
        storage = self.get_storage()
        response = self.get_response()
        storage.add(constants.INFO, "test")
        for m in storage:
            pass  # Iterate through the storage to simulate consumption of messages.
        storage.update(response)
        self.assertEqual(response.cookies["messages"].value, "")
        self.assertEqual(response.cookies["messages"]["domain"], ".example.com")
        self.assertEqual(
            response.cookies["messages"]["expires"], "Thu, 01 Jan 1970 00:00:00 GMT"
        )
        self.assertEqual(
            response.cookies["messages"]["samesite"],
            settings.SESSION_COOKIE_SAMESITE,
        )

    def test_get_bad_cookie(self):
        request = self.get_request()
        storage = self.storage_class(request)
        # Set initial (invalid) data.
        example_messages = ["test", "me"]
        set_cookie_data(storage, example_messages, invalid=True)
        # The message actually contains what we expect.
        self.assertEqual(list(storage), [])

    def test_max_cookie_length(self):
        """
        If the data exceeds what is allowed in a cookie, older messages are
        removed before saving (and returned by the ``update`` method).
        """
        storage = self.get_storage()
        response = self.get_response()

        # When storing as a cookie, the cookie has constant overhead of approx
        # 54 chars, and each message has a constant overhead of about 37 chars
        # and a variable overhead of zero in the best case. We aim for a message
        # size which will fit 4 messages into the cookie, but not 5.
        # See also FallbackTest.test_session_fallback
        msg_size = int((CookieStorage.max_cookie_size - 54) / 4.5 - 37)
        first_msg = None
        # Generate the same (tested) content every time that does not get run
        # through zlib compression.
        random.seed(42)
        for i in range(5):
            msg = get_random_string(msg_size)
            storage.add(constants.INFO, msg)
            if i == 0:
                first_msg = msg
        unstored_messages = storage.update(response)

        cookie_storing = self.stored_messages_count(storage, response)
        self.assertEqual(cookie_storing, 4)

        self.assertEqual(len(unstored_messages), 1)
        self.assertEqual(unstored_messages[0].message, first_msg)

    def test_message_rfc6265(self):
        non_compliant_chars = ["\\", ",", ";", '"']
        messages = ["\\te,st", ';m"e', "\u2019", '123"NOTRECEIVED"']
        storage = self.get_storage()
        encoded = storage._encode(messages)
        for illegal in non_compliant_chars:
            self.assertEqual(encoded.find(illegal), -1)

    def test_json_encoder_decoder(self):
        """
        A complex nested data structure containing Message
        instances is properly encoded/decoded by the custom JSON
        encoder/decoder classes.
        """
        messages = [
            {
                "message": Message(constants.INFO, "Test message"),
                "message_list": [
                    Message(constants.INFO, "message %s") for x in range(5)
                ]
                + [{"another-message": Message(constants.ERROR, "error")}],
            },
            Message(constants.INFO, "message %s"),
        ]
        encoder = MessageEncoder()
        value = encoder.encode(messages)
        decoded_messages = json.loads(value, cls=MessageDecoder)
        self.assertEqual(messages, decoded_messages)

    def test_safedata(self):
        """
        A message containing SafeData is keeping its safe status when
        retrieved from the message storage.
        """
        self.assertIsInstance(
            self.encode_decode(mark_safe("<b>Hello Django!</b>")).message,
            SafeData,
        )
        self.assertNotIsInstance(
            self.encode_decode("<b>Hello Django!</b>").message,
            SafeData,
        )

    def test_extra_tags(self):
        """
        A message's extra_tags attribute is correctly preserved when retrieved
        from the message storage.
        """
        for extra_tags in ["", None, "some tags"]:
            with self.subTest(extra_tags=extra_tags):
                self.assertEqual(
                    self.encode_decode("message", extra_tags=extra_tags).extra_tags,
                    extra_tags,
                )


class BisectTests(TestCase):
    def test_bisect_keep_left(self):
        self.assertEqual(bisect_keep_left([1, 1, 1], fn=lambda arr: sum(arr) != 2), 2)
        self.assertEqual(bisect_keep_left([1, 1, 1], fn=lambda arr: sum(arr) != 0), 0)
        self.assertEqual(bisect_keep_left([], fn=lambda arr: sum(arr) != 0), 0)

    def test_bisect_keep_right(self):
        self.assertEqual(bisect_keep_right([1, 1, 1], fn=lambda arr: sum(arr) != 2), 1)
        self.assertEqual(
            bisect_keep_right([1, 1, 1, 1], fn=lambda arr: sum(arr) != 2), 2
        )
        self.assertEqual(
            bisect_keep_right([1, 1, 1, 1, 1], fn=lambda arr: sum(arr) != 1), 4
        )
        self.assertEqual(bisect_keep_right([], fn=lambda arr: sum(arr) != 0), 0)
