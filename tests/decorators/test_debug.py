from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables


class NotAHttpRequest:
    pass


class SensitiveVariablesTests(SimpleTestCase):
    def test_sensitive_variables_without_parameters(self):
        @sensitive_variables()
        def sync_view(request):
            return HttpResponse()

        response = sync_view(HttpRequest())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sync_view.sensitive_variables, "__ALL__")

    def test_sensitive_variables_with_parameters(self):
        @sensitive_variables("a", "b")
        def sync_view(request):
            return HttpResponse()

        response = sync_view(HttpRequest())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sync_view.sensitive_variables, ("a", "b"))

    def test_uncalled_decorator_raises_exception(self):
        error_message = (
            "sensitive_variables() must be called to use it as a decorator, "
            "e.g., use @sensitive_variables(), not @sensitive_variables."
        )

        with self.assertRaisesMessage(TypeError, error_message):

            @sensitive_variables
            def sync_view(request):
                return HttpResponse()


class SensitivePostParametersTests(SimpleTestCase):
    def test_sensitive_post_parameters_without_parameters(self):
        @sensitive_post_parameters()
        def sync_view(request):
            return HttpResponse()

        request = HttpRequest()
        response = sync_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.sensitive_post_parameters, "__ALL__")

    def test_sensitive_post_parameters_with_parameters(self):
        @sensitive_post_parameters("a", "b")
        def sync_view(request):
            return HttpResponse()

        request = HttpRequest()
        response = sync_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.sensitive_post_parameters, ("a", "b"))

    def test_uncalled_decorator_raises_exception(self):
        error_message = (
            "sensitive_post_parameters() must be called to use it as a "
            "decorator, e.g., use @sensitive_post_parameters(), not "
            "@sensitive_post_parameters."
        )

        with self.assertRaisesMessage(TypeError, error_message):

            @sensitive_post_parameters
            def sync_view(request):
                return HttpResponse()

    def test_non_httprequest_as_request_raises_exception(self):
        @sensitive_post_parameters()
        def sync_view(request):
            return HttpResponse()

        error_message = (
            "sensitive_post_parameters didn't receive an HttpRequest "
            "object. If you are decorating a classmethod, make sure "
            "to use @method_decorator."
        )

        with self.assertRaisesMessage(TypeError, error_message):
            sync_view(NotAHttpRequest())
