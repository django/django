from django.contrib.messages import constants
from django.contrib.messages.tests.base import BaseTest
from django.contrib.messages.storage.cookie import CookieStorage, \
                                            MessageEncoder, MessageDecoder
from django.contrib.messages.storage.base import Message
from django.utils import simplejson as json


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


class CookieTest(BaseTest):
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
        self.assertTrue(unstored_messages[0].message == '0' * msg_size)

    def test_json_encoder_decoder(self):
        """
        Tests that a complex nested data structure containing Message
        instances is properly encoded/decoded by the custom JSON
        encoder/decoder classes.
        """
        messages = [
            {
                'message': Message(constants.INFO, 'Test message'),
                'message_list': [Message(constants.INFO, 'message %s') \
                                 for x in xrange(5)] + [{'another-message': \
                                 Message(constants.ERROR, 'error')}],
            },
            Message(constants.INFO, 'message %s'),
        ]
        encoder = MessageEncoder(separators=(',', ':'))
        value = encoder.encode(messages)
        decoded_messages = json.loads(value, cls=MessageDecoder)
        self.assertEqual(messages, decoded_messages)
