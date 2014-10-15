from django.test import LiveServerTestCase

from django.contrib.staticfiles.handlers import StaticFilesHandler


class StaticLiveServerTestCase(LiveServerTestCase):
    """
    Extends django.test.LiveServerTestCase to transparently overlay at test
    execution-time the assets provided by the staticfiles app finders. This
    means you don't need to run collectstatic before or as a part of your tests
    setup.
    """

    static_handler = StaticFilesHandler
