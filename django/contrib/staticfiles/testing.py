from django.test import LiveServerTestCase

from django.contrib.staticfiles.handlers import StaticFilesHandler


class StaticLiveServerCase(LiveServerTestCase):

    static_handler = StaticFilesHandler
