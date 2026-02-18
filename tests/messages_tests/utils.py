from django.contrib.messages import Message
from django.contrib.messages.storage.session import SessionStorage


class DummyStorage:
    """Dummy message-store to test the API methods."""

    def __init__(self):
        self.store = []

    def add(self, level, message, extra_tags="", extra_kwargs=None):
        self.store.append(Message(level, message, extra_tags, extra_kwargs))

    def __iter__(self):
        return iter(self.store)


class PermanentStorage(SessionStorage):
    "Example storage to test custom message class"

    def __iter__(self):
        self.used = True
        if self._queued_messages:
            self._loaded_messages.extend(self._queued_messages)
            self._queued_messages = []

        for message in self._loaded_messages:
            # re-add permanent messages to _queued_messages
            if (
                hasattr(message, "extra_kwargs")
                and message.extra_kwargs
                and message.extra_kwargs.get("permanent")
            ):
                self._queued_messages.append(message)

        return iter(self._loaded_messages)
