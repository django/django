import logging

from django.conf import settings
from django.views.debug import ExceptionReporter


class MyHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.config = settings.LOGGING


class CustomExceptionReporter(ExceptionReporter):
    def get_traceback_text(self):
        return "custom traceback text"
