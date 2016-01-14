"""
Since this file contains Python 3 specific syntax, it's named without a test_
prefix so the test runner won't try to import it. Instead, the test class is
imported in test_debug.py, but only on Python 3.

This filename is also in setup.cfg flake8 exclude since the Python 2 syntax
error (raise ... from ...) can't be silenced using NOQA.
"""
import sys

from django.test import RequestFactory, TestCase
from django.views.debug import ExceptionReporter


class Py3ExceptionReporterTests(TestCase):

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

        explicit_exc = 'The above exception ({0}) was the direct cause of the following exception:'
        implicit_exc = 'During handling of the above exception ({0}), another exception occurred:'

        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        # Both messages are twice on page -- one rendered as html,
        # one as plain text (for pastebin)
        self.assertEqual(2, html.count(explicit_exc.format("Top level")))
        self.assertEqual(2, html.count(implicit_exc.format("Second exception")))

        text = reporter.get_traceback_text()
        self.assertIn(explicit_exc.format("Top level"), text)
        self.assertIn(implicit_exc.format("Second exception"), text)
