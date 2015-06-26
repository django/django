from django.conf import settings
from django.contrib import messages
from django.test.extensions import TestExtension


class MessagesOutbox(TestExtension):
    def setup_environment(self):
        self._original_message_storage = settings.MESSAGE_STORAGE
        settings.MESSAGE_STORAGE = 'django.contrib.messages.storage.locmem.MemoryStorage'
        messages.outbox = []

    def teardown_environment(self):
        settings.MESSAGE_STORAGE = self._original_message_storage
        del self._original_message_storge
        del messages.outbox

    def setup_test(self):
        messages.outbox = []
