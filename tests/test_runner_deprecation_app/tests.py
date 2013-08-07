import warnings

from django.test import TestCase

warnings.warn("module-level warning from deprecation_app", DeprecationWarning)

class DummyTest(TestCase):
    def test_warn(self):
        warnings.warn("warning from test", DeprecationWarning)
