from django import http
from django.core.exceptions import PermissionDenied
from django.template import engines
from django.template.response import TemplateResponse


def normal_view(request):
    return http.HttpResponse('OK')


def template_response(request):
    template = engines['django'].from_string('template_response OK{% for m in mw %}\n{{ m }}{% endfor %}')
    return TemplateResponse(request, template, context={'mw': []})


def template_response_error(request):
    template = engines['django'].from_string('{%')
    return TemplateResponse(request, template)


def not_found(request):
    raise http.Http404()


def server_error(request):
    raise Exception('Error in view')


def null_view(request):
    return None


def permission_denied(request):
    raise PermissionDenied()


def exception_in_render(request):
    class CustomHttpResponse(http.HttpResponse):
        def render(self):
            raise Exception('Exception in HttpResponse.render()')

    return CustomHttpResponse('Error')
