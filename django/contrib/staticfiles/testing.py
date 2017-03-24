import warnings

from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.test import LiveServerTestCase
from django.utils.deprecation import RemovedInDjango30Warning


class StaticLiveServerTestCase(LiveServerTestCase):
    """
    Extend django.test.LiveServerTestCase to transparently overlay at test
    execution-time the assets provided by the staticfiles app finders. This
    means you don't need to run collectstatic before or as a part of your tests
    setup.
    """

    def __init__(self, methodName='runTest'):
        warnings.warn(
            "django.contrib.staticfiles.testing.StaticLifeServerTestCase is deprecated",
            RemovedInDjango30Warning,
            stacklevel=2,
        )
        super().__init__(methodName=methodName)

    static_handler = StaticFilesHandler
