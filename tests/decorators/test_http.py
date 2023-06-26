import datetime

from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.test import SimpleTestCase
from django.views.decorators.http import condition, require_http_methods, require_safe


class RequireHttpMethodsTest(SimpleTestCase):
    def test_require_http_methods_methods(self):
        @require_http_methods(["GET", "PUT"])
        def my_view(request):
            return HttpResponse("OK")

        request = HttpRequest()
        request.method = "GET"
        self.assertIsInstance(my_view(request), HttpResponse)
        request.method = "PUT"
        self.assertIsInstance(my_view(request), HttpResponse)
        request.method = "HEAD"
        self.assertIsInstance(my_view(request), HttpResponseNotAllowed)
        request.method = "POST"
        self.assertIsInstance(my_view(request), HttpResponseNotAllowed)
        request.method = "DELETE"
        self.assertIsInstance(my_view(request), HttpResponseNotAllowed)


class RequireSafeDecoratorTest(SimpleTestCase):
    def test_require_safe_accepts_only_safe_methods(self):
        def my_view(request):
            return HttpResponse("OK")

        my_safe_view = require_safe(my_view)
        request = HttpRequest()
        request.method = "GET"
        self.assertIsInstance(my_safe_view(request), HttpResponse)
        request.method = "HEAD"
        self.assertIsInstance(my_safe_view(request), HttpResponse)
        request.method = "POST"
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)
        request.method = "PUT"
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)
        request.method = "DELETE"
        self.assertIsInstance(my_safe_view(request), HttpResponseNotAllowed)


class ConditionDecoratorTest(SimpleTestCase):
    def etag_func(request, *args, **kwargs):
        return '"b4246ffc4f62314ca13147c9d4f76974"'

    def latest_entry(request, *args, **kwargs):
        return datetime.datetime(2023, 1, 2, 23, 21, 47)

    def test_condition_decorator(self):
        @condition(
            etag_func=self.etag_func,
            last_modified_func=self.latest_entry,
        )
        def my_view(request):
            return HttpResponse()

        request = HttpRequest()
        request.method = "GET"
        response = my_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["ETag"], '"b4246ffc4f62314ca13147c9d4f76974"')
        self.assertEqual(
            response.headers["Last-Modified"],
            "Mon, 02 Jan 2023 23:21:47 GMT",
        )
