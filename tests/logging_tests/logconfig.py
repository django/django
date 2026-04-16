import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.views.debug import ExceptionReporter


class MyHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.config = settings.LOGGING


# RemovedInDjango70Warning.
class MyEmailBackend(BaseEmailBackend):
    sent_messages = []

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(**kwargs)
        self.fail_silently = fail_silently
        self.__class__.sent_messages[:] = []

    def send_messages(self, email_messages):
        self.__class__.sent_messages.extend(email_messages)


class CustomExceptionReporter(ExceptionReporter):
    def get_traceback_text(self):
        return "custom traceback text"
