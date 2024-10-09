"""A custom backend for testing."""

from django.core.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_outbox = []

    def send_messages(self, email_messages):
        # Messages are stored in an instance variable for testing.
        self.test_outbox.extend(email_messages)
        return len(email_messages)


class FailingEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        raise ValueError("FailingEmailBackend is doomed to fail.")
