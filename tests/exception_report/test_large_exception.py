import sys

from django.test import TestCase
from django.test.client import RequestFactory
from django.views.debug import ExceptionReporter


class ExceptionReport(TestCase):
    factory = RequestFactory()

    def test_large_sizable_object(self):
        lg = list(range(50 * 1024 * 1024))
        try:
            request = self.factory.get("/")
            lg["a"]
        except TypeError:
            exc_type, exc_value, tb = sys.exc_info()

        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        d = reporter.get_traceback_data()
        vars = d["lastframe"]["vars"]

        for k, v in vars:
            if k == "lg":
                i = v.index("...")
                # Check if it has been trimmed
                self.assertGreater(i, -1)

                # Construct list with elements before trimming
                ls = eval(v[:i] + "]")

                # Check if length of trimmed list is our limit
                self.assertEqual(len(ls), 4096)
                break

    def test_non_sizable_object(self):
        num = 10000000
        try:
            request = self.factory.get("/")
            num["a"]
        except TypeError:
            exc_type, exc_value, tb = sys.exc_info()

        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        d = reporter.get_traceback_data()
        vars = d["lastframe"]["vars"]

        for k, v in vars:
            if k == "a":
                self.assertEqual(v, str(num))
                break
