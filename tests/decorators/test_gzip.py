from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase
from django.views.decorators.gzip import gzip_page


class GzipPageTests(SimpleTestCase):
    # Gzip ignores content that is too short.
    content = "Content " * 100

    def test_gzip_page_decorator(self):
        @gzip_page
        def sync_view(request):
            return HttpResponse(content=self.content)

        request = HttpRequest()
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip"
        response = sync_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Encoding"), "gzip")
