"""
Backend for test environment.
"""

import copy

from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    """
    An email backend for use during test sessions.

    The test connection stores email messages in a dummy outbox,
    rather than sending them out on the wire.

    The dummy outbox is accessible through the outbox instance attribute.
    """

    def __init__(self, **kwargs):
        # RemovedInDjango70Warning: locmem backend must consume username and
        # password when send_mail() is called with deprecated auth_user or
        # auth_password (to avoid extra deprecation warnings).
        if kwargs.get("alias") is None:
            kwargs.pop("username", None)
            kwargs.pop("password", None)
        super().__init__(**kwargs)
        if not hasattr(mail, "outbox"):
            mail.outbox = []

    def send_messages(self, messages):
        """Redirect messages to the dummy outbox"""
        msg_count = 0
        for message in messages:
            message.message()  # Triggers header validation.
            msg_copy = copy.deepcopy(message)
            msg_copy.sent_using = self.alias
            mail.outbox.append(msg_copy)
            msg_count += 1
        return msg_count
