"""A custom backend for testing."""

from django.core import mail
from django.core.mail.backends import dummy, locmem
from django.core.mail.backends.base import BaseEmailBackend
from django.test import ignore_warnings
from django.utils.deprecation import RemovedInDjango70Warning


class EmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_outbox = []

    def send_messages(self, email_messages):
        # Messages are stored in an instance variable for testing.
        self.test_outbox.extend(email_messages)
        return len(email_messages)


class FailingEmailBackend(BaseEmailBackend):

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(**kwargs)
        self.fail_silently = fail_silently

    def send_messages(self, email_messages):
        if self.fail_silently:
            return 0
        raise ValueError("FailingEmailBackend is doomed to fail.")


# RemovedInDjango70Warning.
class OptionsCapturingBackend(locmem.EmailBackend):
    """Capture the kwargs used to initialize the backend.

    Extend the testing backend to add a `backend_init_kwargs` property to each
    mail.outbox entry, set to the kwargs used to initialize the backend.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs.copy()
        msg = r".*BaseEmailBackend will raise a TypeError for unknown keyword arguments"
        with ignore_warnings(category=RemovedInDjango70Warning, message=msg):
            super().__init__(**kwargs)

    def send_messages(self, email_messages):
        previous_outbox_len = len(mail.outbox)
        result = super().send_messages(email_messages)
        for email in mail.outbox[previous_outbox_len:]:
            email.backend_init_kwargs = self.kwargs
        return result


class InitCheckBackend(dummy.EmailBackend):

    init_kwargs = None

    def __init__(self, alias=None, **kwargs):
        super().__init__(alias=alias)
        self.__class__.init_kwargs = kwargs
