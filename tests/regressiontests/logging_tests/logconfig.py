import logging

from django.conf import settings

class MyHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.config = settings.LOGGING
