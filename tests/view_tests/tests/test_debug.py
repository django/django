import importlib
import inspect
import os
import re
import sys
import tempfile
from io import StringIO
from pathlib import Path

from django.conf.urls import url
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.utils import LoggingCaptureMixin, patch_logger
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.functional import SimpleLazyObject
from django.views.debug import (
    CLEANSED_SUBSTITUTE, CallableSettingWrapper, ExceptionReporter,
    cleanse_setting, technical_500_response,
)

from ..views import (
    custom_exception_reporter_filter_view, index_page,
    multivalue_dict_key_error, non_sensitive_view, paranoid_view,
    sensitive_args_function_caller, sensitive_kwargs_function_caller,
    sensitive_method_view, sensitive_view,
)

PY36 = sys.version_info >= (3, 6)


class User:
    def __str__(self):
        return 'jacob'


class WithoutEmptyPathUrls:
    urlpatterns = [url(r'url/$', index_page, name='url')]


class CallableSettingWrapperTests(SimpleTestCase):
    """ Unittests for CallableSettingWrapper
    """
    def test_repr(self):
        class WrappedCallable:
            def __repr__(self):
                return "repr from the wrapped callable"

            def __call__(self):
                pass

        actual = repr(CallableSettingWrapper(WrappedCallable()))
        self.assertEqual(actual, "repr from the wrapped callable")


@override_settings(DEBUG=True, ROOT_URLCONF='view_tests.urls')
class DebugViewTests(LoggingCaptureMixin, SimpleTestCase):

    def test_files(self):
        response = self.client.get('/raises/')
        self.assertEqual(response.status_code, 500)

        data = {
            'file_data.txt': SimpleUploadedFile('file_data.txt', b'haha'),
        }
        response = self.client.post('/raises/', data)
        self.assertContains(response, 'file_data.txt', status_code=500)
        self.assertNotContains(response, 'haha', status_code=500)

    def test_400(self):
        # When DEBUG=True, technical_500_template() is called.
        response = self.client.get('/raises400/')
        self.assertContains(response, '<div class="context" id="', status_code=400)

    # Ensure no 403.html template exists to test the default case.
    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    }])
    def test_403(self):
        response = self.client.get('/raises403/')
        self.assertContains(response, '<h1>403 Forbidden</h1>', status_code=403)

    # Set up a test 403.html template.
    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.locmem.Loader', {
                    '403.html': 'This is a test template for a 403 error ({{ exception }}).',
                }),
            ],
        },
    }])
    def test_403_template(self):
        response = self.client.get('/raises403/')
        self.assertContains(response, 'test template', status_code=403)
        self.assertContains(response, '(Insufficient Permissions).', status_code=403)

    def test_404(self):
        response = self.client.get('/raises404/')
        self.assertEqual(response.status_code, 404)

    def test_raised_404(self):
        response = self.client.get('/views/raises404/')
        self.assertContains(response, "<code>not-in-urls</code>, didn't match", status_code=404)

    def test_404_not_in_urls(self):
        response = self.client.get('/not-in-urls')
        self.assertNotContains(response, "Raised by:", status_code=404)
        self.assertContains(response, "<code>not-in-urls</code>, didn't match", status_code=404)

    @override_settings(ROOT_URLCONF=WithoutEmptyPathUrls)
    def test_404_empty_path_not_in_urls(self):
        response = self.client.get('/')
        self.assertContains(response, "The empty path didn't match any of these.", status_code=404)

    def test_technical_404(self):
        response = self.client.get('/views/technical404/')
        self.assertContains(response, "Raised by:", status_code=404)
        self.assertContains(response, "view_tests.views.technical404", status_code=404)

    def test_classbased_technical_404(self):
        response = self.client.get('/views/classbased404/')
        self.assertContains(response, "Raised by:", status_code=404)
        self.assertContains(response, "view_tests.views.Http404View", status_code=404)

    def test_non_l10ned_numeric_ids(self):
        """
        Numeric IDs and fancy traceback context blocks line numbers shouldn't be localized.
        """
        with self.settings(DEBUG=True, USE_L10N=True):
            response = self.client.get('/raises500/')
            # We look for a HTML fragment of the form
            # '<div class="context" id="c38123208">', not '<div class="context" id="c38,123,208"'
            self.assertContains(response, '<div class="context" id="', status_code=500)
            match = re.search(b'<div class="context" id="(?P<id>[^"]+)">', response.content)
            self.assertIsNotNone(match)
            id_repr = match.group('id')
            self.assertFalse(
                re.search(b'[^c0-9]', id_repr),
                "Numeric IDs in debug response HTML page shouldn't be localized (value: %s)." % id_repr.decode()
            )

    def test_template_exceptions(self):
        try:
            self.client.get(reverse('template_exception'))
        except Exception:
            raising_loc = inspect.trace()[-1][-2][0].strip()
            self.assertNotEqual(
                raising_loc.find("raise Exception('boom')"), -1,
                "Failed to find 'raise Exception' in last frame of "
                "traceback, instead found: %s" % raising_loc
            )

    def test_template_loader_postmortem(self):
        """Tests for not existing file"""
        template_name = "notfound.html"
        with tempfile.NamedTemporaryFile(prefix=template_name) as tmpfile:
            tempdir = os.path.dirname(tmpfile.name)
            template_path = os.path.join(tempdir, template_name)
            with override_settings(TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [tempdir],
            }]):
                response = self.client.get(reverse('raises_template_does_not_exist', kwargs={"path": template_name}))
            self.assertContains(response, "%s (Source does not exist)" % template_path, status_code=500, count=2)
            # Assert as HTML.
            self.assertContains(
                response,
                '<li><code>django.template.loaders.filesystem.Loader</code>: '
                '%s (Source does not exist)</li>' % os.path.join(tempdir, 'notfound.html'),
                status_code=500,
                html=True,
            )

    def test_no_template_source_loaders(self):
        """
        Make sure if you don't specify a template, the debug view doesn't blow up.
        """
        with self.assertRaises(TemplateDoesNotExist):
            self.client.get('/render_no_template/')

    @override_settings(ROOT_URLCONF='view_tests.default_urls')
    def test_default_urlconf_template(self):
        """
        Make sure that the default URLconf template is shown shown instead
        of the technical 404 page, if the user has not altered their
        URLconf yet.
        """
        response = self.client.get('/')
        self.assertContains(
            response,
            "<h2>Congratulations on your first Django-powered page.</h2>"
        )

    @override_settings(ROOT_URLCONF='view_tests.regression_21530_urls')
    def test_regression_21530(self):
        """
        Regression test for bug #21530.

        If the admin app include is replaced with exactly one url
        pattern, then the technical 404 template should be displayed.

        The bug here was that an AttributeError caused a 500 response.
        """
        response = self.client.get('/')
        self.assertContains(
            response,
            "Page not found <span>(404)</span>",
            status_code=404
        )


class DebugViewQueriesAllowedTests(SimpleTestCase):
    # May need a query to initialize MySQL connection
    allow_database_queries = True

    def test_handle_db_exception(self):
        """
        Ensure the debug view works when a database exception is raised by
        performing an invalid query and passing the exception to the debug view.
        """
        with connection.cursor() as cursor:
            try:
                cursor.execute('INVALID SQL')
            except DatabaseError:
                exc_info = sys.exc_info()

        rf = RequestFactory()
        response = technical_500_response(rf.get('/'), *exc_info)
        self.assertContains(response, 'OperationalError at /', status_code=500)


@override_settings(
    DEBUG=True,
    ROOT_URLCONF='view_tests.urls',
    # No template directories are configured, so no templates will be found.
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.dummy.TemplateStrings',
    }],
)
class NonDjangoTemplatesDebugViewTests(SimpleTestCase):

    def test_400(self):
        # When DEBUG=True, technical_500_template() is called.
        with patch_logger('django.security.SuspiciousOperation', 'error'):
            response = self.client.get('/raises400/')
            self.assertContains(response, '<div class="context" id="', status_code=400)

    def test_403(self):
        response = self.client.get('/raises403/')
        self.assertContains(response, '<h1>403 Forbidden</h1>', status_code=403)

    def test_404(self):
        response = self.client.get('/raises404/')
        self.assertEqual(response.status_code, 404)

    def test_template_not_found_error(self):
        # Raises a TemplateDoesNotExist exception and shows the debug view.
        url = reverse('raises_template_does_not_exist', kwargs={"path": "notfound.html"})
        response = self.client.get(url)
        self.assertContains(response, '<div class="context" id="', status_code=500)


class ExceptionReporterTests(SimpleTestCase):
    rf = RequestFactory()

    def test_request_and_exception(self):
        "A simple exception report can be generated"
        try:
            request = self.rf.get('/test_view/')
            request.user = User()
            raise ValueError("Can't find my keys")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertInHTML('<h1>ValueError at /test_view/</h1>', html)
        self.assertIn('<pre class="exception_value">Can&#39;t find my keys</pre>', html)
        self.assertIn('<th>Request Method:</th>', html)
        self.assertIn('<th>Request URL:</th>', html)
        self.assertIn('<h3 id="user-info">USER</h3>', html)
        self.assertIn('<p>jacob</p>', html)
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
        self.assertInHTML('<h1>ValueError</h1>', html)
        self.assertIn('<pre class="exception_value">Can&#39;t find my keys</pre>', html)
        self.assertNotIn('<th>Request Method:</th>', html)
        self.assertNotIn('<th>Request URL:</th>', html)
        self.assertNotIn('<h3 id="user-info">USER</h3>', html)
        self.assertIn('<th>Exception Type:</th>', html)
        self.assertIn('<th>Exception Value:</th>', html)
        self.assertIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertIn('<p>Request data not supplied</p>', html)

    def test_eol_support(self):
        """The ExceptionReporter supports Unix, Windows and Macintosh EOL markers"""
        LINES = list('print %d' % i for i in range(1, 6))
        reporter = ExceptionReporter(None, None, None, None)

        for newline in ['\n', '\r\n', '\r']:
            fd, filename = tempfile.mkstemp(text=False)
            os.write(fd, force_bytes(newline.join(LINES) + newline))
            os.close(fd)

            try:
                self.assertEqual(
                    reporter._get_lines_from_file(filename, 3, 2),
                    (1, LINES[1:3], LINES[3], LINES[4:])
                )
            finally:
                os.unlink(filename)

    def test_no_exception(self):
        "An exception report can be generated for just a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, None, None)
        html = reporter.get_traceback_html()
        self.assertInHTML('<h1>Report at /test_view/</h1>', html)
        self.assertIn('<pre class="exception_value">No exception message supplied</pre>', html)
        self.assertIn('<th>Request Method:</th>', html)
        self.assertIn('<th>Request URL:</th>', html)
        self.assertNotIn('<th>Exception Type:</th>', html)
        self.assertNotIn('<th>Exception Value:</th>', html)
        self.assertNotIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertNotIn('<p>Request data not supplied</p>', html)

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

    def test_request_and_message(self):
        "A message can be provided in addition to a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, "I'm a little teapot", None)
        html = reporter.get_traceback_html()
        self.assertInHTML('<h1>Report at /test_view/</h1>', html)
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
        self.assertInHTML('<h1>Report</h1>', html)
        self.assertIn('<pre class="exception_value">I&#39;m a little teapot</pre>', html)
        self.assertNotIn('<th>Request Method:</th>', html)
        self.assertNotIn('<th>Request URL:</th>', html)
        self.assertNotIn('<th>Exception Type:</th>', html)
        self.assertNotIn('<th>Exception Value:</th>', html)
        self.assertNotIn('<h2>Traceback ', html)
        self.assertIn('<h2>Request information</h2>', html)
        self.assertIn('<p>Request data not supplied</p>', html)

    def test_non_utf8_values_handling(self):
        "Non-UTF-8 exceptions/values should not make the output generation choke."
        try:
            class NonUtf8Output(Exception):
                def __repr__(self):
                    return b'EXC\xe9EXC'
            somevar = b'VAL\xe9VAL'  # NOQA
            raise NonUtf8Output()
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(None, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertIn('VAL\\xe9VAL', html)
        self.assertIn('EXC\\xe9EXC', html)

    def test_unprintable_values_handling(self):
        "Unprintable values should not make the output generation choke."
        try:
            class OomOutput:
                def __repr__(self):
                    raise MemoryError('OOM')
            oomvalue = OomOutput()  # NOQA
            raise ValueError()
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(None, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertIn('<td class="code"><pre>Error in formatting', html)

    def test_too_large_values_handling(self):
        "Large values should not create a large HTML."
        large = 256 * 1024
        repr_of_str_adds = len(repr(''))
        try:
            class LargeOutput:
                def __repr__(self):
                    return repr('A' * large)
            largevalue = LargeOutput()  # NOQA
            raise ValueError()
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(None, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertEqual(len(html) // 1024 // 128, 0)  # still fit in 128Kb
        self.assertIn('&lt;trimmed %d bytes string&gt;' % (large + repr_of_str_adds,), html)

    def test_unfrozen_importlib(self):
        """
        importlib is not a frozen app, but its loader thinks it's frozen which
        results in an ImportError. Refs #21443.
        """
        try:
            request = self.rf.get('/test_view/')
            importlib.import_module('abc.def.invalid.name')
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertInHTML('<h1>%sError at /test_view/</h1>' % ('ModuleNotFound' if PY36 else 'Import'), html)

    def test_ignore_traceback_evaluation_exceptions(self):
        """
        Don't trip over exceptions generated by crafted objects when
        evaluating them while cleansing (#24455).
        """
        class BrokenEvaluation(Exception):
            pass

        def broken_setup():
            raise BrokenEvaluation

        request = self.rf.get('/test_view/')
        broken_lazy = SimpleLazyObject(broken_setup)
        try:
            bool(broken_lazy)
        except BrokenEvaluation:
            exc_type, exc_value, tb = sys.exc_info()

        self.assertIn(
            "BrokenEvaluation",
            ExceptionReporter(request, exc_type, exc_value, tb).get_traceback_html(),
            "Evaluation exception reason not mentioned in traceback"
        )

    @override_settings(ALLOWED_HOSTS='example.com')
    def test_disallowed_host(self):
        "An exception report can be generated even for a disallowed host."
        request = self.rf.get('/', HTTP_HOST='evil.com')
        reporter = ExceptionReporter(request, None, None, None)
        html = reporter.get_traceback_html()
        self.assertIn("http://evil.com/", html)

    def test_request_with_items_key(self):
        """
        An exception report can be generated for requests with 'items' in
        request GET, POST, FILES, or COOKIES QueryDicts.
        """
        value = '<td>items</td><td class="code"><pre>&#39;Oops&#39;</pre></td>'
        # GET
        request = self.rf.get('/test_view/?items=Oops')
        reporter = ExceptionReporter(request, None, None, None)
        html = reporter.get_traceback_html()
        self.assertInHTML(value, html)
        # POST
        request = self.rf.post('/test_view/', data={'items': 'Oops'})
        reporter = ExceptionReporter(request, None, None, None)
        html = reporter.get_traceback_html()
        self.assertInHTML(value, html)
        # FILES
        fp = StringIO('filecontent')
        request = self.rf.post('/test_view/', data={'name': 'filename', 'items': fp})
        reporter = ExceptionReporter(request, None, None, None)
        html = reporter.get_traceback_html()
        self.assertInHTML(
            '<td>items</td><td class="code"><pre>&lt;InMemoryUploadedFile: '
            'items (application/octet-stream)&gt;</pre></td>',
            html
        )
        # COOKES
        rf = RequestFactory()
        rf.cookies['items'] = 'Oops'
        request = rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, None, None)
        html = reporter.get_traceback_html()
        self.assertInHTML('<td>items</td><td class="code"><pre>&#39;Oops&#39;</pre></td>', html)

    def test_exception_fetching_user(self):
        """
        The error page can be rendered if the current user can't be retrieved
        (such as when the database is unavailable).
        """
        class ExceptionUser:
            def __str__(self):
                raise Exception()

        request = self.rf.get('/test_view/')
        request.user = ExceptionUser()

        try:
            raise ValueError('Oops')
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()

        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertInHTML('<h1>ValueError at /test_view/</h1>', html)
        self.assertIn('<pre class="exception_value">Oops</pre>', html)
        self.assertIn('<h3 id="user-info">USER</h3>', html)
        self.assertIn('<p>[unable to retrieve the current user]</p>', html)

        text = reporter.get_traceback_text()
        self.assertIn('USER: [unable to retrieve the current user]', text)


class PlainTextReportTests(SimpleTestCase):
    rf = RequestFactory()

    def test_request_and_exception(self):
        "A simple exception report can be generated"
        try:
            request = self.rf.get('/test_view/')
            request.user = User()
            raise ValueError("Can't find my keys")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        text = reporter.get_traceback_text()
        self.assertIn('ValueError at /test_view/', text)
        self.assertIn("Can't find my keys", text)
        self.assertIn('Request Method:', text)
        self.assertIn('Request URL:', text)
        self.assertIn('USER: jacob', text)
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
        self.assertNotIn('USER:', text)
        self.assertIn('Exception Type:', text)
        self.assertIn('Exception Value:', text)
        self.assertIn('Traceback:', text)
        self.assertIn('Request data not supplied', text)

    def test_no_exception(self):
        "An exception report can be generated for just a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, None, None)
        reporter.get_traceback_text()

    def test_request_and_message(self):
        "A message can be provided in addition to a request"
        request = self.rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, "I'm a little teapot", None)
        reporter.get_traceback_text()

    @override_settings(DEBUG=True)
    def test_template_exception(self):
        request = self.rf.get('/test_view/')
        try:
            render(request, 'debug/template_error.html')
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        text = reporter.get_traceback_text()
        templ_path = Path(Path(__file__).parent.parent, 'templates', 'debug', 'template_error.html')
        self.assertIn(
            'Template error:\n'
            'In template %(path)s, error at line 2\n'
            '   \'cycle\' tag requires at least two arguments\n'
            '   1 : Template with error:\n'
            '   2 :  {%% cycle %%} \n'
            '   3 : ' % {'path': templ_path},
            text
        )

    def test_request_with_items_key(self):
        """
        An exception report can be generated for requests with 'items' in
        request GET, POST, FILES, or COOKIES QueryDicts.
        """
        # GET
        request = self.rf.get('/test_view/?items=Oops')
        reporter = ExceptionReporter(request, None, None, None)
        text = reporter.get_traceback_text()
        self.assertIn("items = 'Oops'", text)
        # POST
        request = self.rf.post('/test_view/', data={'items': 'Oops'})
        reporter = ExceptionReporter(request, None, None, None)
        text = reporter.get_traceback_text()
        self.assertIn("items = 'Oops'", text)
        # FILES
        fp = StringIO('filecontent')
        request = self.rf.post('/test_view/', data={'name': 'filename', 'items': fp})
        reporter = ExceptionReporter(request, None, None, None)
        text = reporter.get_traceback_text()
        self.assertIn('items = <InMemoryUploadedFile:', text)
        # COOKES
        rf = RequestFactory()
        rf.cookies['items'] = 'Oops'
        request = rf.get('/test_view/')
        reporter = ExceptionReporter(request, None, None, None)
        text = reporter.get_traceback_text()
        self.assertIn("items = 'Oops'", text)

    def test_message_only(self):
        reporter = ExceptionReporter(None, None, "I'm a little teapot", None)
        reporter.get_traceback_text()

    @override_settings(ALLOWED_HOSTS='example.com')
    def test_disallowed_host(self):
        "An exception report can be generated even for a disallowed host."
        request = self.rf.get('/', HTTP_HOST='evil.com')
        reporter = ExceptionReporter(request, None, None, None)
        text = reporter.get_traceback_text()
        self.assertIn("http://evil.com/", text)


class ExceptionReportTestMixin:

    # Mixin used in the ExceptionReporterFilterTests and
    # AjaxResponseExceptionReporterFilter tests below

    breakfast_data = {'sausage-key': 'sausage-value',
                      'baked-beans-key': 'baked-beans-value',
                      'hash-brown-key': 'hash-brown-value',
                      'bacon-key': 'bacon-value'}

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
        with self.settings(ADMINS=[('Admin', 'admin@fattie-breakie.com')]):
            mail.outbox = []  # Empty outbox
            request = self.rf.post('/some_url/', self.breakfast_data)
            view(request)
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]

            # Frames vars are never shown in plain text email reports.
            body_plain = str(email.body)
            self.assertNotIn('cooked_eggs', body_plain)
            self.assertNotIn('scrambled', body_plain)
            self.assertNotIn('sauce', body_plain)
            self.assertNotIn('worcestershire', body_plain)

            # Frames vars are shown in html email reports.
            body_html = str(email.alternatives[0][0])
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
        with self.settings(ADMINS=[('Admin', 'admin@fattie-breakie.com')]):
            mail.outbox = []  # Empty outbox
            request = self.rf.post('/some_url/', self.breakfast_data)
            view(request)
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]

            # Frames vars are never shown in plain text email reports.
            body_plain = str(email.body)
            self.assertNotIn('cooked_eggs', body_plain)
            self.assertNotIn('scrambled', body_plain)
            self.assertNotIn('sauce', body_plain)
            self.assertNotIn('worcestershire', body_plain)

            # Frames vars are shown in html email reports.
            body_html = str(email.alternatives[0][0])
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
        with self.settings(ADMINS=[('Admin', 'admin@fattie-breakie.com')]):
            mail.outbox = []  # Empty outbox
            request = self.rf.post('/some_url/', self.breakfast_data)
            view(request)
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            # Frames vars are never shown in plain text email reports.
            body = str(email.body)
            self.assertNotIn('cooked_eggs', body)
            self.assertNotIn('scrambled', body)
            self.assertNotIn('sauce', body)
            self.assertNotIn('worcestershire', body)
            for k, v in self.breakfast_data.items():
                # All POST parameters' names are shown.
                self.assertIn(k, body)
                # No POST parameters' values are shown.
                self.assertNotIn(v, body)


@override_settings(ROOT_URLCONF='view_tests.urls')
class ExceptionReporterFilterTests(ExceptionReportTestMixin, LoggingCaptureMixin, SimpleTestCase):
    """
    Sensitive information can be filtered out of error reports (#14614).
    """
    rf = RequestFactory()

    def test_non_sensitive_request(self):
        """
        Everything (request info and frame variables) can bee seen
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
        Sensitive POST parameters and frame variables cannot be
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
        No POST parameters and frame variables can be seen in the
        default error reports for "paranoid" requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(paranoid_view)
            self.verify_unsafe_email(paranoid_view)

        with self.settings(DEBUG=False):
            self.verify_paranoid_response(paranoid_view)
            self.verify_paranoid_email(paranoid_view)

    def test_multivalue_dict_key_error(self):
        """
        #21098 -- Sensitive POST parameters cannot be seen in the
        error reports for if request.POST['nonexistent_key'] throws an error.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(multivalue_dict_key_error)
            self.verify_unsafe_email(multivalue_dict_key_error)

        with self.settings(DEBUG=False):
            self.verify_safe_response(multivalue_dict_key_error)
            self.verify_safe_email(multivalue_dict_key_error)

    def test_custom_exception_reporter_filter(self):
        """
        It's possible to assign an exception reporter filter to
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
        The sensitive_variables decorator works with object methods.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_method_view, check_for_POST_params=False)
            self.verify_unsafe_email(sensitive_method_view, check_for_POST_params=False)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_method_view, check_for_POST_params=False)
            self.verify_safe_email(sensitive_method_view, check_for_POST_params=False)

    def test_sensitive_function_arguments(self):
        """
        Sensitive variables don't leak in the sensitive_variables decorator's
        frame, when those variables are passed as arguments to the decorated
        function.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_args_function_caller)
            self.verify_unsafe_email(sensitive_args_function_caller)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_args_function_caller, check_for_POST_params=False)
            self.verify_safe_email(sensitive_args_function_caller, check_for_POST_params=False)

    def test_sensitive_function_keyword_arguments(self):
        """
        Sensitive variables don't leak in the sensitive_variables decorator's
        frame, when those variables are passed as keyword arguments to the
        decorated function.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_kwargs_function_caller)
            self.verify_unsafe_email(sensitive_kwargs_function_caller)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_kwargs_function_caller, check_for_POST_params=False)
            self.verify_safe_email(sensitive_kwargs_function_caller, check_for_POST_params=False)

    def test_callable_settings(self):
        """
        Callable settings should not be evaluated in the debug page (#21345).
        """
        def callable_setting():
            return "This should not be displayed"
        with self.settings(DEBUG=True, FOOBAR=callable_setting):
            response = self.client.get('/raises500/')
            self.assertNotContains(response, "This should not be displayed", status_code=500)

    def test_callable_settings_forbidding_to_set_attributes(self):
        """
        Callable settings which forbid to set attributes should not break
        the debug page (#23070).
        """
        class CallableSettingWithSlots:
            __slots__ = []

            def __call__(self):
                return "This should not be displayed"

        with self.settings(DEBUG=True, WITH_SLOTS=CallableSettingWithSlots()):
            response = self.client.get('/raises500/')
            self.assertNotContains(response, "This should not be displayed", status_code=500)

    def test_dict_setting_with_non_str_key(self):
        """
        A dict setting containing a non-string key should not break the
        debug page (#12744).
        """
        with self.settings(DEBUG=True, FOOBAR={42: None}):
            response = self.client.get('/raises500/')
            self.assertContains(response, 'FOOBAR', status_code=500)

    def test_sensitive_settings(self):
        """
        The debug page should not show some sensitive settings
        (password, secret key, ...).
        """
        sensitive_settings = [
            'SECRET_KEY',
            'PASSWORD',
            'API_KEY',
            'AUTH_TOKEN',
        ]
        for setting in sensitive_settings:
            with self.settings(DEBUG=True, **{setting: "should not be displayed"}):
                response = self.client.get('/raises500/')
                self.assertNotContains(response, 'should not be displayed', status_code=500)

    def test_settings_with_sensitive_keys(self):
        """
        The debug page should filter out some sensitive information found in
        dict settings.
        """
        sensitive_settings = [
            'SECRET_KEY',
            'PASSWORD',
            'API_KEY',
            'AUTH_TOKEN',
        ]
        for setting in sensitive_settings:
            FOOBAR = {
                setting: "should not be displayed",
                'recursive': {setting: "should not be displayed"},
            }
            with self.settings(DEBUG=True, FOOBAR=FOOBAR):
                response = self.client.get('/raises500/')
                self.assertNotContains(response, 'should not be displayed', status_code=500)


class AjaxResponseExceptionReporterFilter(ExceptionReportTestMixin, LoggingCaptureMixin, SimpleTestCase):
    """
    Sensitive information can be filtered out of error reports.

    Here we specifically test the plain text 500 debug-only error page served
    when it has been detected the request was sent by JS code. We don't check
    for (non)existence of frames vars in the traceback information section of
    the response content because we don't include them in these error pages.
    Refs #14614.
    """
    rf = RequestFactory(HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_non_sensitive_request(self):
        """
        Request info can bee seen in the default error reports for
        non-sensitive requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(non_sensitive_view, check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_unsafe_response(non_sensitive_view, check_for_vars=False)

    def test_sensitive_request(self):
        """
        Sensitive POST parameters cannot be seen in the default
        error reports for sensitive requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(sensitive_view, check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_safe_response(sensitive_view, check_for_vars=False)

    def test_paranoid_request(self):
        """
        No POST parameters can be seen in the default error reports
        for "paranoid" requests.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(paranoid_view, check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_paranoid_response(paranoid_view, check_for_vars=False)

    def test_custom_exception_reporter_filter(self):
        """
        It's possible to assign an exception reporter filter to
        the request to bypass the one set in DEFAULT_EXCEPTION_REPORTER_FILTER.
        """
        with self.settings(DEBUG=True):
            self.verify_unsafe_response(custom_exception_reporter_filter_view, check_for_vars=False)

        with self.settings(DEBUG=False):
            self.verify_unsafe_response(custom_exception_reporter_filter_view, check_for_vars=False)


class HelperFunctionTests(SimpleTestCase):

    def test_cleanse_setting_basic(self):
        self.assertEqual(cleanse_setting('TEST', 'TEST'), 'TEST')
        self.assertEqual(cleanse_setting('PASSWORD', 'super_secret'), CLEANSED_SUBSTITUTE)

    def test_cleanse_setting_ignore_case(self):
        self.assertEqual(cleanse_setting('password', 'super_secret'), CLEANSED_SUBSTITUTE)

    def test_cleanse_setting_recurses_in_dictionary(self):
        initial = {'login': 'cooper', 'password': 'secret'}
        expected = {'login': 'cooper', 'password': CLEANSED_SUBSTITUTE}
        self.assertEqual(cleanse_setting('SETTING_NAME', initial), expected)
