# -*- coding: utf-8 -*-
# This coding header is significant for tests, as the debug view is parsing
# files to search for such a header to decode the source file content
from __future__ import absolute_import, unicode_literals

import inspect
import os
import sys

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory
from django.test.utils import (override_settings, setup_test_template_loader,
    restore_template_loaders)
from django.utils.encoding import force_text
from django.views.debug import ExceptionReporter

from .. import BrokenException, except_args
from ..views import (sensitive_view, non_sensitive_view, paranoid_view,
    custom_exception_reporter_filter_view, sensitive_method_view,
    sensitive_args_function_caller, sensitive_kwargs_function_caller)


@override_settings(DEBUG=True, TEMPLATE_DEBUG=True)
class DebugViewTests(TestCase):
    urls = "regressiontests.views.urls"

    def test_files(self):
        response = self.client.get('/raises/')
        self.assertEqual(response.status_code, 500)

        data = {
            'file_data.txt': SimpleUploadedFile('file_data.txt', b'haha'),
        }
        response = self.client.post('/raises/', data)
        self.assertContains(response, 'file_data.txt', status_code=500)
        self.assertNotContains(response, 'haha', status_code=500)

    def test_403(self):
        # Ensure no 403.html template exists to test the default case.
        setup_test_template_loader({})
        try:
            response = self.client.get('/views/raises403/')
            self.assertContains(response, '<h1>403 Forbidden</h1>', status_code=403)
        finally:
            restore_template_loaders()

    def test_403_template(self):
        # Set up a test 403.html template.
        setup_test_template_loader(
            {'403.html': 'This is a test template for a 403 Forbidden error.'}
        )
        try:
            response = self.client.get('/views/raises403/')
            self.assertContains(response, 'test template', status_code=403)
        finally:
            restore_template_loaders()

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
            except Exception:
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


class PlainTextReportTests(TestCase):
    rf = RequestFactory()

    def test_request_and_exception(self):
        "A simple exception report can be generated"
        try:
            request = self.rf.get('/test_view/')
            raise ValueError("Can't find my keys")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        text = reporter.get_traceback_text()
        self.assertIn('ValueError at /test_view/', text)
        self.assertIn("Can't find my keys", text)
        self.assertIn('Request Method:', text)
        self.assertIn('Request URL:', text)
        self.assertIn('Exception Type:', text)
        self.assertIn('Exception Value:', text)
        self.assertIn('Traceback:', text)
        self.assertIn('Request information:', text)
        self.assertNotIn('Request data not supplied', text)

    def test_no_request(self):
        "An exception report can be generated without request"
        try:
            raise ValueError("Can't find my keys")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(None, exc_type, exc_value, tb)
        text = reporter.get_traceback_text()
        self.assertIn('ValueError', text)
        self.assertIn("Can't find my keys", text)
        self.assertNotIn('Request Method:', text)
        self.assertNotIn('Request URL:', text)
        self.assertIn('Exception Type:', text)
        self.assertIn('Exception Value:', text)
        self.assertIn('Traceback:', text)
        self.assertIn('Request data not supplied', text)

    def test_no_exception(self):
        "An exception report can be generated for just a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, None, None)
        text = reporter.get_traceback_text()

    def test_request_and_message(self):
        "A message can be provided in addition to a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, "I'm a little teapot", None)
        text = reporter.get_traceback_text()

    def test_message_only(self):
        reporter = ExceptionReporter(None, None, "I'm a little teapot", None)
        text = reporter.get_traceback_text()


class ExceptionReportTestMixin(object):

    # Mixin used in the ExceptionReporterFilterTests and
    # AjaxResponseExceptionReporterFilter tests below

    breakfast_data = {'sausage-key': 'sausage-value',
                      'baked-beans-key': 'baked-beans-value',
                      'hash-brown-key': 'hash-brown-value',
                      'bacon-key': 'bacon-value',}

    def verify_unsafe_response(self, view, check_for_vars=True,
                               check_for_POST_params=True):
        """
        Asserts that potentially sensitive info are displayed in the response.
        """
        request = self.rf.post('/some_url/', self.breakfast_data)
        response = view(request)
        if check_for_vars:
            # All variables are shown.
            self.assertContains(response, 'cooked_eggs', status_code=500)
            self.assertContains(response, 'scrambled', status_code=500)
            self.assertContains(response, 'sauce', status_code=500)
            self.assertContains(response, 'worcestershire', status_code=500)
        if check_for_POST_params:
            for k, v in self.breakfast_data.items():
                # All POST parameters are shown.
                self.assertContains(response, k, status_code=500)
                self.assertContains(response, v, status_code=500)

    def verify_safe_response(self, view, check_for_vars=True,
                             check_for_POST_params=True):
        """
        Asserts that certain sensitive info are not displayed in the response.
        """
        request = self.rf.post('/some_url/', self.breakfast_data)
        response = view(request)
        if check_for_vars:
            # Non-sensitive variable's name and value are shown.
            self.assertContains(response, 'cooked_eggs', status_code=500)
            self.assertContains(response, 'scrambled', status_code=500)
            # Sensitive variable's name is shown but not its value.
            self.assertContains(response, 'sauce', status_code=500)
            self.assertNotContains(response, 'worcestershire', status_code=500)
        if check_for_POST_params:
            for k, v in self.breakfast_data.items():
                # All POST parameters' names are shown.
                self.assertContains(response, k, status_code=500)
            # Non-sensitive POST parameters' values are shown.
            self.assertContains(response, 'baked-beans-value', status_code=500)
            self.assertContains(response, 'hash-brown-value', status_code=500)
            # Sensitive POST parameters' values are not shown.
            self.assertNotContains(response, 'sausage-value', status_code=500)
            self.assertNotContains(response, 'bacon-value', status_code=500)

    def verify_paranoid_response(self, view, check_for_vars=True,
                                 check_for_POST_params=True):
        """
        Asserts that no variables or POST parameters are displayed in the response.
        """
        request = self.rf.post('/some_url/', self.breakfast_data)
        response = view(request)
        if check_for_vars:
            # Show variable names but not their values.
            self.assertContains(response, 'cooked_eggs', status_code=500)
            self.assertNotContains(response, 'scrambled', status_code=500)
            self.assertContains(response, 'sauce', status_code=500)
            self.assertNotContains(response, 'worcestershire', status_code=500)
        if check_for_POST_params:
            for k, v in self.breakfast_data.items():
                # All POST parameters' names are shown.
                self.assertContains(response, k, status_code=500)
                # No POST parameters' values are shown.
                self.assertNotContains(response, v, status_code=500)

    def verify_unsafe_email(self, view, check_for_POST_params=True):
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
            body_plain = force_text(email.body)
            self.assertNotIn('cooked_eggs', body_plain)
            self.assertNotIn('scrambled', body_plain)
            self.assertNotIn('sauce', body_plain)
            self.assertNotIn('worcestershire', body_plain)

            # Frames vars are shown in html email reports.
            body_html = force_text(email.alternatives[0][0])
            self.assertIn('cooked_eggs', body_html)
            self.assertIn('scrambled', body_html)
            self.assertIn('sauce', body_html)
            self.assertIn('worcestershire', body_html)

            if check_for_POST_params:
                for k, v in self.breakfast_data.items():
                    # All POST parameters are shown.
                    self.assertIn(k, body_plain)
                    self.assertIn(v, body_plain)
                    self.assertIn(k, body_html)
                    self.assertIn(v, body_html)

    def verify_safe_email(self, view, check_for_POST_params=True):
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
            body_plain = force_text(email.body)
            self.assertNotIn('cooked_eggs', body_plain)
            self.assertNotIn('scrambled', body_plain)
            self.assertNotIn('sauce', body_plain)
            self.assertNotIn('worcestershire', body_plain)

            # Frames vars are shown in html email reports.
            body_html = force_text(email.alternatives[0][0])
            self.assertIn('cooked_eggs', body_html)
            self.assertIn('scrambled', body_html)
            self.assertIn('sauce', body_html)
            self.assertNotIn('worcestershire', body_html)

            if check_for_POST_params:
                for k, v in self.breakfast_data.items():
                    # All POST parameters' names are shown.
                    self.assertIn(k, body_plain)
                # Non-sensitive POST parameters' values are shown.
                self.assertIn('baked-beans-value', body_plain)
                self.assertIn('hash-brown-value', body_plain)
                self.assertIn('baked-beans-value', body_html)
                self.assertIn('hash-brown-value', body_html)
                # Sensitive POST parameters' values are not shown.
                self.assertNotIn('sausage-value', body_plain)
                self.assertNotIn('bacon-value', body_plain)
                self.assertNotIn('sausage-value', body_html)
                self.assertNotIn('bacon-value', body_html)

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
            body = force_text(email.body)
            self.assertNotIn('cooked_eggs', body)
            self.assertNotIn('scrambled', body)
            self.assertNotIn('sauce', body)
            self.assertNotIn('worcestershire', body)
            for k, v in self.breakfast_data.items():
                # All POST parameters' names are shown.
                self.assertIn(k, body)
                # No POST parameters' values are shown.
                self.assertNotIn(v, body)


class ExceptionReporterFilterTests(TestCase, ExceptionReportTestMixin):
    """
    Ensure that sensitive information can be filtered out of error reports.
    Refs #14614.
    """
    rf = RequestFactory()

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

    def test_sensitive_method(self):
        """
        Ensure that the sensitive_variables decorator works with object
        methods.
        Refs #18379.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_method_view,
                                        check_for_POST_params=False)
            self.verify_unsafe_email(sensitive_method_view,
                                     check_for_POST_params=False)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_method_view,
                                      check_for_POST_params=False)
            self.verify_safe_email(sensitive_method_view,
                                   check_for_POST_params=False)

    def test_sensitive_function_arguments(self):
        """
        Ensure that sensitive variables don't leak in the sensitive_variables
        decorator's frame, when those variables are passed as arguments to the
        decorated function.
        Refs #19453.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_args_function_caller)
            self.verify_unsafe_email(sensitive_args_function_caller)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_args_function_caller, check_for_POST_params=False)
            self.verify_safe_email(sensitive_args_function_caller, check_for_POST_params=False)

    def test_sensitive_function_keyword_arguments(self):
        """
        Ensure that sensitive variables don't leak in the sensitive_variables
        decorator's frame, when those variables are passed as keyword arguments
        to the decorated function.
        Refs #19453.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_kwargs_function_caller)
            self.verify_unsafe_email(sensitive_kwargs_function_caller)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_kwargs_function_caller, check_for_POST_params=False)
            self.verify_safe_email(sensitive_kwargs_function_caller, check_for_POST_params=False)


class AjaxResponseExceptionReporterFilter(TestCase, ExceptionReportTestMixin):
    """
    Ensure that sensitive information can be filtered out of error reports.

    Here we specifically test the plain text 500 debug-only error page served
    when it has been detected the request was sent by JS code. We don't check
    for (non)existence of frames vars in the traceback information section of
    the response content because we don't include them in these error pages.
    Refs #14614.
    """
    rf = RequestFactory(HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_non_sensitive_request(self):
        """
        Ensure that request info can bee seen in the default error reports for
        non-sensitive requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(non_sensitive_view, check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_unsafe_response(non_sensitive_view, check_for_vars=False)

    def test_sensitive_request(self):
        """
        Ensure that sensitive POST parameters cannot be seen in the default
        error reports for sensitive requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_view, check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_view, check_for_vars=False)

    def test_paranoid_request(self):
        """
        Ensure that no POST parameters can be seen in the default error reports
        for "paranoid" requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(paranoid_view, check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_paranoid_response(paranoid_view, check_for_vars=False)

    def test_custom_exception_reporter_filter(self):
        """
        Ensure that it's possible to assign an exception reporter filter to
        the request to bypass the one set in DEFAULT_EXCEPTION_REPORTER_FILTER.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(custom_exception_reporter_filter_view,
                check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_unsafe_response(custom_exception_reporter_filter_view,
                check_for_vars=False)
