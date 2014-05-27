import logging

from freedom.conf import settings
from freedom.core.mail.backends.base import BaseEmailBackend


class MyHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.config = settings.LOGGING


class MyEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        pass
