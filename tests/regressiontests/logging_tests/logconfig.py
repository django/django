import logging

from django.conf import settings

class MyHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        self.config = settings.LOGGING
