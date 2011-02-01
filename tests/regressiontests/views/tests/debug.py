import inspect
import sys

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, RequestFactory
from django.core.urlresolvers import reverse
from django.template import TemplateSyntaxError
from django.views.debug import ExceptionReporter

from regressiontests.views import BrokenException, except_args


class DebugViewTests(TestCase):
    def setUp(self):
        self.old_debug = settings.DEBUG
        settings.DEBUG = True
        self.old_template_debug = settings.TEMPLATE_DEBUG
        settings.TEMPLATE_DEBUG = True

    def tearDown(self):
        settings.DEBUG = self.old_debug
        settings.TEMPLATE_DEBUG = self.old_template_debug

    def test_files(self):
        response = self.client.get('/views/raises/')
        self.assertEquals(response.status_code, 500)

        data = {
            'file_data.txt': SimpleUploadedFile('file_data.txt', 'haha'),
        }
        response = self.client.post('/views/raises/', data)
        self.assertTrue('file_data.txt' in response.content)
        self.assertFalse('haha' in response.content)

    def test_404(self):
        response = self.client.get('/views/raises404/')
        self.assertEquals(response.status_code, 404)

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
        self.assertContains(response, 'templates/i_dont_exist.html</code> (File does not exist)</li>', status_code=500)


class ExceptionReporterTests(TestCase):
    rf = RequestFactory()

    def test_request_and_exception(self):
        "A simple exception report can be generated"
        try:
            request = self.rf.get('/test_view/')
            raise KeyError("Can't find my keys")
        except KeyError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(request, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertIn('<h1>KeyError at /test_view/</h1>', html)
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
            raise KeyError("Can't find my keys")
        except KeyError:
            exc_type, exc_value, tb = sys.exc_info()
        reporter = ExceptionReporter(None, exc_type, exc_value, tb)
        html = reporter.get_traceback_html()
        self.assertIn('<h1>KeyError</h1>', html)
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
