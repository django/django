# tests/views/test_sensitive_data.py
from django.test import SimpleTestCase, RequestFactory
from django.views.debug import ExceptionReporter
from django.views.decorators.debug import sensitive_post_parameters

@sensitive_post_parameters('password')
def dummy_view(request):
    password = request.POST.get('password')
    raise ValueError("Intentional error for testing sensitive data")


class SensitiveDataLeakTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_password_not_in_exception_email(self):
        password = '$0m3P4$$w0rd'

        # Create a proper HttpRequest object
        request = self.factory.post('/', data={'username': 'testuser', 'password': password})

        try:
            dummy_view(request)
        except ValueError:
            import sys
            exc_type, exc_value, tb = sys.exc_info()

        reporter = ExceptionReporter(
            request=request,
            is_email=True,
            exc_type=exc_type,
            exc_value=exc_value,
            tb=tb
        )

        html_email = reporter.get_traceback_html()
        self.assertNotIn(password, html_email)