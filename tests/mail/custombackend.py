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


class OptionsCapturingBackend(BaseEmailBackend):
    """Capture init kwargs and sent messages for use in test assertions.

    Test cases using this backend _must_ ensure reset() is called::

        def test_something(self):
            self.addCleanup(OptionsCapturingBackend.reset)
            ...

    Failing to call reset() will cause unexpected behavior in other tests that
    use the OptionsCapturingBackend.
    """

    init_kwargs = []
    sent_messages = []

    @classmethod
    def reset(cls):
        cls.init_kwargs = []
        cls.sent_messages = []

    def __init__(self, **kwargs):
        self.init_kwargs.append(kwargs.copy())
        super().__init__(**kwargs)

    def send_messages(self, email_messages):
        self.sent_messages.extend(email_messages)
        return len(email_messages)


class FailingEmailBackend(OptionsCapturingBackend):
    """Raise on send_messages(), or do nothing if fail_silently is set.

    Test cases using this backend _must_ ensure reset() is called::

        def test_something(self):
            self.addCleanup(FailingEmailBackend.reset)
            ...

    Failing to call reset() will cause unexpected behavior in other tests that
    use the FailingEmailBackend.
    """

    init_kwargs = []
    sent_messages = []

    def send_messages(self, email_messages):
        if self.fail_silently:
            return 0
        raise ValueError("FailingEmailBackend is doomed to fail.")
