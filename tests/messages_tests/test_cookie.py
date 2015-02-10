import json

from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.cookie import (
    CookieStorage, MessageDecoder, MessageEncoder,
)
from django.test import TestCase, override_settings
from django.utils.safestring import SafeData, mark_safe

from .base import BaseTests


def set_cookie_data(storage, messages, invalid=False, encode_empty=False):
    """
    Sets ``request.COOKIES`` with the encoded data and removes the storage
    backend's loaded data cache.
    """
    encoded_data = storage._encode(messages, encode_empty=encode_empty)
    if invalid:
        # Truncate the first character so that the hash is invalid.
        encoded_data = encoded_data[1:]
    storage.request.COOKIES = {CookieStorage.cookie_name: encoded_data}
    if hasattr(storage, '_loaded_data'):
        del storage._loaded_data


def stored_cookie_messages_count(storage, response):
    """
    Returns an integer containing the number of messages stored.
    """
    # Get a list of cookies, excluding ones with a max-age of 0 (because
    # they have been marked for deletion).
    cookie = response.cookies.get(storage.cookie_name)
    if not cookie or cookie['max-age'] == 0:
        return 0
    data = storage._decode(cookie.value)
    if not data:
        return 0
    if data[-1] == CookieStorage.not_finished:
        data.pop()
    return len(data)


@override_settings(SESSION_COOKIE_DOMAIN='.example.com', SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True)
class CookieTest(BaseTests, TestCase):
    storage_class = CookieStorage

    def stored_messages_count(self, storage, response):
        return stored_cookie_messages_count(storage, response)

    def test_get(self):
        storage = self.storage_class(self.get_request())
        # Set initial data.
        example_messages = ['test', 'me']
        set_cookie_data(storage, example_messages)
        # Test that the message actually contains what we expect.
        self.assertEqual(list(storage), example_messages)

    def test_cookie_setings(self):
        """
        Ensure that CookieStorage honors SESSION_COOKIE_DOMAIN, SESSION_COOKIE_SECURE and SESSION_COOKIE_HTTPONLY
        Refs #15618 and #20972.
        """
        # Test before the messages have been consumed
        storage = self.get_storage()
        response = self.get_response()
        storage.add(constants.INFO, 'test')
        storage.update(response)
        self.assertIn('test', response.cookies['messages'].value)
        self.assertEqual(response.cookies['messages']['domain'], '.example.com')
        self.assertEqual(response.cookies['messages']['expires'], '')
        self.assertEqual(response.cookies['messages']['secure'], True)
        self.assertEqual(response.cookies['messages']['httponly'], True)

        # Test deletion of the cookie (storing with an empty value) after the messages have been consumed
        storage = self.get_storage()
        response = self.get_response()
        storage.add(constants.INFO, 'test')
        for m in storage:
            pass  # Iterate through the storage to simulate consumption of messages.
        storage.update(response)
        self.assertEqual(response.cookies['messages'].value, '')
        self.assertEqual(response.cookies['messages']['domain'], '.example.com')
        self.assertEqual(response.cookies['messages']['expires'], 'Thu, 01-Jan-1970 00:00:00 GMT')

    def test_get_bad_cookie(self):
        request = self.get_request()
        storage = self.storage_class(request)
        # Set initial (invalid) data.
        example_messages = ['test', 'me']
        set_cookie_data(storage, example_messages, invalid=True)
        # Test that the message actually contains what we expect.
        self.assertEqual(list(storage), [])

    def test_max_cookie_length(self):
        """
        Tests that, if the data exceeds what is allowed in a cookie, older
        messages are removed before saving (and returned by the ``update``
        method).
        """
        storage = self.get_storage()
        response = self.get_response()

        # When storing as a cookie, the cookie has constant overhead of approx
        # 54 chars, and each message has a constant overhead of about 37 chars
        # and a variable overhead of zero in the best case. We aim for a message
        # size which will fit 4 messages into the cookie, but not 5.
        # See also FallbackTest.test_session_fallback
        msg_size = int((CookieStorage.max_cookie_size - 54) / 4.5 - 37)
        for i in range(5):
            storage.add(constants.INFO, str(i) * msg_size)
        unstored_messages = storage.update(response)

        cookie_storing = self.stored_messages_count(storage, response)
        self.assertEqual(cookie_storing, 4)

        self.assertEqual(len(unstored_messages), 1)
        self.assertEqual(unstored_messages[0].message, '0' * msg_size)

    def test_json_encoder_decoder(self):
        """
        Tests that a complex nested data structure containing Message
        instances is properly encoded/decoded by the custom JSON
        encoder/decoder classes.
        """
        messages = [
            {
                'message': Message(constants.INFO, 'Test message'),
                'message_list': [Message(constants.INFO, 'message %s')
                                 for x in range(5)] + [{'another-message':
                                 Message(constants.ERROR, 'error')}],
            },
            Message(constants.INFO, 'message %s'),
        ]
        encoder = MessageEncoder(separators=(',', ':'))
        value = encoder.encode(messages)
        decoded_messages = json.loads(value, cls=MessageDecoder)
        self.assertEqual(messages, decoded_messages)

    def test_safedata(self):
        """
        Tests that a message containing SafeData is keeping its safe status when
        retrieved from the message storage.
        """
        def encode_decode(data):
            message = Message(constants.DEBUG, data)
            encoded = storage._encode(message)
            decoded = storage._decode(encoded)
            return decoded.message

        storage = self.get_storage()

        self.assertIsInstance(
            encode_decode(mark_safe("<b>Hello Django!</b>")), SafeData)
        self.assertNotIsInstance(
            encode_decode("<b>Hello Django!</b>"), SafeData)

    def test_pre_1_5_message_format(self):
        """
        For ticket #22426. Tests whether messages that were set in the cookie
        before the addition of is_safedata are decoded correctly.
        """

        # Encode the messages using the current encoder.
        messages = [Message(constants.INFO, 'message %s') for x in range(5)]
        encoder = MessageEncoder(separators=(',', ':'))
        encoded_messages = encoder.encode(messages)

        # Remove the is_safedata flag from the messages in order to imitate
        # the behavior of before 1.5 (monkey patching).
        encoded_messages = json.loads(encoded_messages)
        for obj in encoded_messages:
            obj.pop(1)
        encoded_messages = json.dumps(encoded_messages, separators=(',', ':'))

        # Decode the messages in the old format (without is_safedata)
        decoded_messages = json.loads(encoded_messages, cls=MessageDecoder)
        self.assertEqual(messages, decoded_messages)
