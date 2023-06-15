from django.contrib.messages import Message


class DummyStorage:
    """Dummy message-store to test the API methods."""

    def __init__(self):
        self.store = []

    def add(self, level, message, extra_tags=""):
        self.store.append(Message(level, message, extra_tags))

    def __iter__(self):
        return iter(self.store)
