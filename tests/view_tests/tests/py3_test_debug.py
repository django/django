import sys

from django.test import RequestFactory, TestCase
from django.views.debug import ExceptionReporter


class Py3ExceptionReporterTests(TestCase):
    """
    This test case contains Python 3 specific syntax
    which can't be imported in Python 2.x
    """
    rf = RequestFactory()

    def test_reporting_of_nested_exceptions(self):
        request = self.rf.get('/test_view/')
        try:
            try:
                raise AttributeError('Top level')
            except AttributeError as explicit:
                try:
                    raise ValueError('Second exception') from explicit
                except ValueError:
                    raise IndexError('Final exception')
        except Exception:
            # Custom exception handler, just pass it into ExceptionReporter
            exc_type, exc_value, tb = sys.exc_info()

        explicit_exc = ('The above exception ({0}) was the direct'
                        ' cause of the following exception:')
        implicit_exc = ('During handling of the above exception ({0}),'
                        ' another exception occurred:')
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertIn(explicit_exc.format("Top level"), html)
        self.assertIn(implicit_exc.format("Second exception"), html)

        text = reporter.get_traceback_text()
        self.assertIn(explicit_exc.format("Top level"), text)
        self.assertIn(implicit_exc.format("Second exception"), text)
