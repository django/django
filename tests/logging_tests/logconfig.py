import logging

from mango.conf import settings
from mango.core.mail.backends.base import BaseEmailBackend
from mango.views.debug import ExceptionReporter


class MyHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.config = settings.LOGGING


class MyEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        pass


class CustomExceptionReporter(ExceptionReporter):
    def get_traceback_text(self):
        return 'custom traceback text'
