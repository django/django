import warnings

from django.test import TestCase

class DummyTest(TestCase):
    def test_warn(self):
        warnings.warn("warning from test", DeprecationWarning)


