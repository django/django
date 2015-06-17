from django.conf.urls import url
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.test import SimpleTestCase, override_settings


def template_response_error_handler(request, exception=None):
    return TemplateResponse(request, 'test_handler.html', status=403)


def permission_denied_view(request):
    raise PermissionDenied


urlpatterns = [
    url(r'^$', permission_denied_view),
]

handler403 = template_response_error_handler


@override_settings(ROOT_URLCONF='handlers.tests_custom_error_handlers')
class CustomErrorHandlerTests(SimpleTestCase):

    def test_custom_handler(self):
        response = self.client.get('/')
        # We need to force template rendering
        response.content
        self.assertContains(response, 'Error handler content', status_code=403)
