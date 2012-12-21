from django.contrib.messages import constants
from django.contrib.messages.tests.base import BaseTest
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.session import SessionStorage
from django.utils.safestring import SafeData, mark_safe


def set_session_data(storage, messages):
    """
    Sets the messages into the backend request's session and remove the
    backend's loaded data cache.
    """
    storage.request.session[storage.session_key] = messages
    if hasattr(storage, '_loaded_data'):
        del storage._loaded_data


def stored_session_messages_count(storage):
    data = storage.request.session.get(storage.session_key, [])
    return len(data)


class SessionTest(BaseTest):
    storage_class = SessionStorage

    def get_request(self):
        self.session = {}
        request = super(SessionTest, self).get_request()
        request.session = self.session
        return request

    def stored_messages_count(self, storage, response):
        return stored_session_messages_count(storage)

    def test_get(self):
        storage = self.storage_class(self.get_request())
        # Set initial data.
        example_messages = ['test', 'me']
        set_session_data(storage, example_messages)
        # Test that the message actually contains what we expect.
        self.assertEqual(list(storage), example_messages)

    def test_safedata(self):
        """
        Tests that a message containing SafeData is keeping its safe status when
        retrieved from the message storage.
        """
        storage = self.get_storage()

        message = Message(constants.DEBUG, mark_safe("<b>Hello Django!</b>"))
        set_session_data(storage, [message])
        self.assertIsInstance(list(storage)[0].message, SafeData)
