import warnings

from freedom.test import TestCase
from freedom.utils.deprecation import RemovedInNextVersionWarning

warnings.warn("module-level warning from deprecation_app", RemovedInNextVersionWarning)


class DummyTest(TestCase):
    def test_warn(self):
        warnings.warn("warning from test", RemovedInNextVersionWarning)
