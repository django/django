from django.contrib import messages
from django.contrib.messages.storage.base import BaseStorage


class MemoryStorage(BaseStorage):

    def _store(self, messages_to_store, response, *args, **kwargs):
        if not hasattr(messages, 'outbox'):
            messages.outbox = []
        messages.outbox.extend(messages_to_store)

    def _get(self, *args, **kwargs):
        if not hasattr(messages, 'outbox'):
            messages.outbox = []
        return (messages.outbox, True)
