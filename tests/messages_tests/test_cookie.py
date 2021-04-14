import binascii
import json
import random

from django.conf import settings
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.cookie import (
    CookieStorage, MessageDecoder, MessageEncoder,
)
from django.core.signing import b64_decode, get_cookie_signer
from django.test import SimpleTestCase, override_settings
from django.test.utils import ignore_warnings
from django.utils.crypto import get_random_string
from django.utils.deprecation import RemovedInDjango40Warning
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
    if hasattr(storage, '_loaded_data'):
        del storage._loaded_data


def stored_cookie_messages_count(storage, response):
    """
    Return an integer containing the number of messages stored.
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
class CookieTests(BaseTests, SimpleTestCase):
    storage_class = CookieStorage

    def stored_messages_count(self, storage, response):
        return stored_cookie_messages_count(storage, response)

    def test_get(self):
        storage = self.storage_class(self.get_request())
        # Set initial data.
        example_messages = ['test', 'me']
        set_cookie_data(storage, example_messages)
        # The message contains what's expected.
        self.assertEqual(list(storage), example_messages)

    @override_settings(SESSION_COOKIE_SAMESITE='Strict')
    def test_cookie_setings(self):
        """
        CookieStorage honors SESSION_COOKIE_DOMAIN, SESSION_COOKIE_SECURE, and
        SESSION_COOKIE_HTTPONLY (#15618, #20972).
        """
        # Test before the messages have been consumed
        storage = self.get_storage()
        response = self.get_response()
        storage.add(constants.INFO, 'test')
        storage.update(response)
        messages = storage._decode(response.cookies['messages'].value)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'test')
        self.assertEqual(response.cookies['messages']['domain'], '.example.com')
        self.assertEqual(response.cookies['messages']['expires'], '')
        self.assertIs(response.cookies['messages']['secure'], True)
        self.assertIs(response.cookies['messages']['httponly'], True)
        self.assertEqual(response.cookies['messages']['samesite'], 'Strict')

        # Test deletion of the cookie (storing with an empty value) after the messages have been consumed
        storage = self.get_storage()
        response = self.get_response()
        storage.add(constants.INFO, 'test')
        for m in storage:
            pass  # Iterate through the storage to simulate consumption of messages.
        storage.update(response)
        self.assertEqual(response.cookies['messages'].value, '')
        self.assertEqual(response.cookies['messages']['domain'], '.example.com')
        self.assertEqual(response.cookies['messages']['expires'], 'Thu, 01 Jan 1970 00:00:00 GMT')
        self.assertEqual(
            response.cookies['messages']['samesite'],
            settings.SESSION_COOKIE_SAMESITE,
        )

    def test_get_bad_cookie(self):
        request = self.get_request()
        storage = self.storage_class(request)
        # Set initial (invalid) data.
        example_messages = ['test', 'me']
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
        non_compliant_chars = ['\\', ',', ';', '"']
        messages = ['\\te,st', ';m"e', '\u2019', '123"NOTRECEIVED"']
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
                'message': Message(constants.INFO, 'Test message'),
                'message_list': [
                    Message(constants.INFO, 'message %s') for x in range(5)
                ] + [{'another-message': Message(constants.ERROR, 'error')}],
            },
            Message(constants.INFO, 'message %s'),
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
        def encode_decode(data):
            message = Message(constants.DEBUG, data)
            encoded = storage._encode(message)
            decoded = storage._decode(encoded)
            return decoded.message

        storage = self.get_storage()
        self.assertIsInstance(encode_decode(mark_safe("<b>Hello Django!</b>")), SafeData)
        self.assertNotIsInstance(encode_decode("<b>Hello Django!</b>"), SafeData)

    def test_legacy_hash_decode(self):
        # RemovedInDjango40Warning: pre-Django 3.1 hashes will be invalid.
        storage = self.storage_class(self.get_request())
        messages = ['this', 'that']
        # Encode/decode a message using the pre-Django 3.1 hash.
        encoder = MessageEncoder()
        value = encoder.encode(messages)
        encoded_messages = '%s$%s' % (storage._legacy_hash(value), value)
        decoded_messages = storage._decode(encoded_messages)
        self.assertEqual(messages, decoded_messages)

    def test_legacy_encode_decode(self):
        # RemovedInDjango41Warning: pre-Django 3.2 encoded messages will be
        # invalid.
        storage = self.storage_class(self.get_request())
        messages = ['this', Message(0, 'Successfully signed in as admin@example.org')]
        # Encode/decode a message using the pre-Django 3.2 format.
        encoder = MessageEncoder()
        value = encoder.encode(messages)
        with self.assertRaises(binascii.Error):
            b64_decode(value.encode())
        signer = get_cookie_signer(salt=storage.key_salt)
        encoded_messages = signer.sign(value)
        decoded_messages = storage._decode(encoded_messages)
        self.assertEqual(messages, decoded_messages)

    @ignore_warnings(category=RemovedInDjango40Warning)
    def test_default_hashing_algorithm(self):
        messages = Message(constants.DEBUG, ['this', 'that'])
        with self.settings(DEFAULT_HASHING_ALGORITHM='sha1'):
            storage = self.get_storage()
            encoded = storage._encode(messages)
            decoded = storage._decode(encoded)
            self.assertEqual(decoded, messages)
        storage_default = self.get_storage()
        self.assertNotEqual(encoded, storage_default._encode(messages))
