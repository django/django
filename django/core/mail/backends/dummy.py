"""
Dummy email backend that does nothing.
"""

from django.core.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        return len(list(email_messages))

    async def asend_messages(self, email_messages):
        return self.send_messages(email_messages)
