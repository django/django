from mango.core.exceptions import PermissionDenied
from mango.http import HttpResponse
from mango.template import engines
from mango.template.response import TemplateResponse


def normal_view(request):
    return HttpResponse('OK')


def template_response(request):
    template = engines['mango'].from_string('template_response OK{% for m in mw %}\n{{ m }}{% endfor %}')
    return TemplateResponse(request, template, context={'mw': []})


def server_error(request):
    raise Exception('Error in view')


def permission_denied(request):
    raise PermissionDenied()


def exception_in_render(request):
    class CustomHttpResponse(HttpResponse):
        def render(self):
            raise Exception('Exception in HttpResponse.render()')

    return CustomHttpResponse('Error')


async def async_exception_in_render(request):
    class CustomHttpResponse(HttpResponse):
        async def render(self):
            raise Exception('Exception in HttpResponse.render()')

    return CustomHttpResponse('Error')
