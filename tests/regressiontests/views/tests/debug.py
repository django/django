from __future__ import with_statement
import inspect
import os
import sys

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory
from django.core.urlresolvers import reverse
from django.template import TemplateSyntaxError
from django.views.debug import ExceptionReporter
from django.core import mail

from regressiontests.views import BrokenException, except_args
from regressiontests.views.views import (sensitive_view, non_sensitive_view,
    paranoid_view, custom_exception_reporter_filter_view)


class DebugViewTests(TestCase):
    urls = "regressiontests.views.urls"

    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_template_debug = settings.TEMPLATE_DEBUG
        settings.TEMPLATE_DEBUG = True

    def tearDown(self):
        settings.DEBUG = self.old_debug
        settings.TEMPLATE_DEBUG = self.old_template_debug

    def test_files(self):
        response = self.client.get('/raises/')
        self.assertEqual(response.status_code, 500)

        data = {
            'file_data.txt': SimpleUploadedFile('file_data.txt', 'haha'),
        }
        response = self.client.post('/raises/', data)
        self.assertTrue('file_data.txt' in response.content)
        self.assertFalse('haha' in response.content)

    def test_404(self):
        response = self.client.get('/views/raises404/')
        self.assertEqual(response.status_code, 404)

    def test_view_exceptions(self):
        for n in range(len(except_args)):
            self.assertRaises(BrokenException, self.client.get,
                reverse('view_exception', args=(n,)))

    def test_template_exceptions(self):
        for n in range(len(except_args)):
            try:
                self.client.get(reverse('template_exception', args=(n,)))
            except TemplateSyntaxError, e:
                raising_loc = inspect.trace()[-1][-2][0].strip()
                self.assertFalse(raising_loc.find('raise BrokenException') == -1,
                    "Failed to find 'raise BrokenException' in last frame of traceback, instead found: %s" %
                        raising_loc)

    def test_template_loader_postmortem(self):
        response = self.client.get(reverse('raises_template_does_not_exist'))
        template_path = os.path.join('templates', 'i_dont_exist.html')
        self.assertContains(response, template_path, status_code=500)


class ExceptionReporterTests(TestCase):
    rf = RequestFactory()

    def test_request_and_exception(self):
        "A simple exception report can be generated"
        try:
            request = self.rf.get('/test_view/')
            raise ValueError("Can't find my keys")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertIn('<h1>ValueError at /test_view/</h1>', html)
        self.assertIn('<pre class="exception_value">Can&#39;t find my keys</pre>', html)
        self.assertIn('<th>Request Method:</th>', html)
        self.assertIn('<th>Request URL:</th>', html)
        self.assertIn('<th>Exception Type:</th>', html)
        self.assertIn('<th>Exception Value:</th>', html)
        self.assertIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertNotIn('<p>Request data not supplied</p>', html)

    def test_no_request(self):
        "An exception report can be generated without request"
        try:
            raise ValueError("Can't find my keys")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(None, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertIn('<h1>ValueError</h1>', html)
        self.assertIn('<pre class="exception_value">Can&#39;t find my keys</pre>', html)
        self.assertNotIn('<th>Request Method:</th>', html)
        self.assertNotIn('<th>Request URL:</th>', html)
        self.assertIn('<th>Exception Type:</th>', html)
        self.assertIn('<th>Exception Value:</th>', html)
        self.assertIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertIn('<p>Request data not supplied</p>', html)

    def test_no_exception(self):
        "An exception report can be generated for just a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, None, None)
        html = reporter.get_traceback_html()
        self.assertIn('<h1>Report at /test_view/</h1>', html)
        self.assertIn('<pre class="exception_value">No exception supplied</pre>', html)
        self.assertIn('<th>Request Method:</th>', html)
        self.assertIn('<th>Request URL:</th>', html)
        self.assertNotIn('<th>Exception Type:</th>', html)
        self.assertNotIn('<th>Exception Value:</th>', html)
        self.assertNotIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertNotIn('<p>Request data not supplied</p>', html)

    def test_request_and_message(self):
        "A message can be provided in addition to a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, "I'm a little teapot", None)
        html = reporter.get_traceback_html()
        self.assertIn('<h1>Report at /test_view/</h1>', html)
        self.assertIn('<pre class="exception_value">I&#39;m a little teapot</pre>', html)
        self.assertIn('<th>Request Method:</th>', html)
        self.assertIn('<th>Request URL:</th>', html)
        self.assertNotIn('<th>Exception Type:</th>', html)
        self.assertNotIn('<th>Exception Value:</th>', html)
        self.assertNotIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertNotIn('<p>Request data not supplied</p>', html)

    def test_message_only(self):
        reporter = ExceptionReporter(None, None, "I'm a little teapot", None)
        html = reporter.get_traceback_html()
        self.assertIn('<h1>Report</h1>', html)
        self.assertIn('<pre class="exception_value">I&#39;m a little teapot</pre>', html)
        self.assertNotIn('<th>Request Method:</th>', html)
        self.assertNotIn('<th>Request URL:</th>', html)
        self.assertNotIn('<th>Exception Type:</th>', html)
        self.assertNotIn('<th>Exception Value:</th>', html)
        self.assertNotIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertIn('<p>Request data not supplied</p>', html)


class ExceptionReporterFilterTests(TestCase):
    """
    Ensure that sensitive information can be filtered out of error reports.
    Refs #14614.
    """
    rf = RequestFactory()
    breakfast_data = {'sausage-key': 'sausage-value',
                      'baked-beans-key': 'baked-beans-value',
                      'hash-brown-key': 'hash-brown-value',
                      'bacon-key': 'bacon-value',}

    def verify_unsafe_response(self, view):
        """
        Asserts that potentially sensitive info are displayed in the response.
        """
        request = self.rf.post('/some_url/', self.breakfast_data)
        response = view(request)
        # All variables are shown.
        self.assertContains(response, 'cooked_eggs', status_code=500)
        self.assertContains(response, 'scrambled', status_code=500)
        self.assertContains(response, 'sauce', status_code=500)
        self.assertContains(response, 'worcestershire', status_code=500)
        for k, v in self.breakfast_data.items():
            # All POST parameters are shown.
            self.assertContains(response, k, status_code=500)
            self.assertContains(response, v, status_code=500)

    def verify_safe_response(self, view):
        """
        Asserts that certain sensitive info are not displayed in the response.
        """
        request = self.rf.post('/some_url/', self.breakfast_data)
        response = view(request)
        # Non-sensitive variable's name and value are shown.
        self.assertContains(response, 'cooked_eggs', status_code=500)
        self.assertContains(response, 'scrambled', status_code=500)
        # Sensitive variable's name is shown but not its value.
        self.assertContains(response, 'sauce', status_code=500)
        self.assertNotContains(response, 'worcestershire', status_code=500)
        for k, v in self.breakfast_data.items():
            # All POST parameters' names are shown.
            self.assertContains(response, k, status_code=500)
        # Non-sensitive POST parameters' values are shown.
        self.assertContains(response, 'baked-beans-value', status_code=500)
        self.assertContains(response, 'hash-brown-value', status_code=500)
        # Sensitive POST parameters' values are not shown.
        self.assertNotContains(response, 'sausage-value', status_code=500)
        self.assertNotContains(response, 'bacon-value', status_code=500)

    def verify_paranoid_response(self, view):
        """
        Asserts that no variables or POST parameters are displayed in the response.
        """
        request = self.rf.post('/some_url/', self.breakfast_data)
        response = view(request)
        # Show variable names but not their values.
        self.assertContains(response, 'cooked_eggs', status_code=500)
        self.assertNotContains(response, 'scrambled', status_code=500)
        self.assertContains(response, 'sauce', status_code=500)
        self.assertNotContains(response, 'worcestershire', status_code=500)
        for k, v in self.breakfast_data.items():
            # All POST parameters' names are shown.
            self.assertContains(response, k, status_code=500)
            # No POST parameters' values are shown.
            self.assertNotContains(response, v, status_code=500)

    def verify_unsafe_email(self, view):
        """
        Asserts that potentially sensitive info are displayed in the email report.
        """
        with self.settings(ADMINS=(('Admin', 'admin@fattie-breakie.com'),)):
            mail.outbox = [] # Empty outbox
            request = self.rf.post('/some_url/', self.breakfast_data)
            response = view(request)
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            # Frames vars are never shown in plain text email reports.
            self.assertNotIn('cooked_eggs', email.body)
            self.assertNotIn('scrambled', email.body)
            self.assertNotIn('sauce', email.body)
            self.assertNotIn('worcestershire', email.body)
            for k, v in self.breakfast_data.items():
                # All POST parameters are shown.
                self.assertIn(k, email.body)
                self.assertIn(v, email.body)

    def verify_safe_email(self, view):
        """
        Asserts that certain sensitive info are not displayed in the email report.
        """
        with self.settings(ADMINS=(('Admin', 'admin@fattie-breakie.com'),)):
            mail.outbox = [] # Empty outbox
            request = self.rf.post('/some_url/', self.breakfast_data)
            response = view(request)
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            # Frames vars are never shown in plain text email reports.
            self.assertNotIn('cooked_eggs', email.body)
            self.assertNotIn('scrambled', email.body)
            self.assertNotIn('sauce', email.body)
            self.assertNotIn('worcestershire', email.body)
            for k, v in self.breakfast_data.items():
                # All POST parameters' names are shown.
                self.assertIn(k, email.body)
            # Non-sensitive POST parameters' values are shown.
            self.assertIn('baked-beans-value', email.body)
            self.assertIn('hash-brown-value', email.body)
            # Sensitive POST parameters' values are not shown.
            self.assertNotIn('sausage-value', email.body)
            self.assertNotIn('bacon-value', email.body)

    def verify_paranoid_email(self, view):
        """
        Asserts that no variables or POST parameters are displayed in the email report.
        """
        with self.settings(ADMINS=(('Admin', 'admin@fattie-breakie.com'),)):
            mail.outbox = [] # Empty outbox
            request = self.rf.post('/some_url/', self.breakfast_data)
            response = view(request)
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            # Frames vars are never shown in plain text email reports.
            self.assertNotIn('cooked_eggs', email.body)
            self.assertNotIn('scrambled', email.body)
            self.assertNotIn('sauce', email.body)
            self.assertNotIn('worcestershire', email.body)
            for k, v in self.breakfast_data.items():
                # All POST parameters' names are shown.
                self.assertIn(k, email.body)
                # No POST parameters' values are shown.
                self.assertNotIn(v, email.body)

    def test_non_sensitive_request(self):
        """
        Ensure that everything (request info and frame variables) can bee seen
        in the default error reports for non-sensitive requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(non_sensitive_view)
            self.verify_unsafe_email(non_sensitive_view)

        with self.settings(DEBUG=False):
            self.verify_unsafe_response(non_sensitive_view)
            self.verify_unsafe_email(non_sensitive_view)

    def test_sensitive_request(self):
        """
        Ensure that sensitive POST parameters and frame variables cannot be
        seen in the default error reports for sensitive requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_view)
            self.verify_unsafe_email(sensitive_view)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_view)
            self.verify_safe_email(sensitive_view)

    def test_paranoid_request(self):
        """
        Ensure that no POST parameters and frame variables can be seen in the
        default error reports for "paranoid" requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(paranoid_view)
            self.verify_unsafe_email(paranoid_view)

        with self.settings(DEBUG=False):
            self.verify_paranoid_response(paranoid_view)
            self.verify_paranoid_email(paranoid_view)

    def test_custom_exception_reporter_filter(self):
        """
        Ensure that it's possible to assign an exception reporter filter to
        the request to bypass the one set in DEFAULT_EXCEPTION_REPORTER_FILTER.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(custom_exception_reporter_filter_view)
            self.verify_unsafe_email(custom_exception_reporter_filter_view)

        with self.settings(DEBUG=False):
            self.verify_unsafe_response(custom_exception_reporter_filter_view)
            self.verify_unsafe_email(custom_exception_reporter_filter_view)
