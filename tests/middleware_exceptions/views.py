from freedom import http
from freedom.core.exceptions import PermissionDenied
from freedom.template import Template
from freedom.template.response import TemplateResponse


def normal_view(request):
    return http.HttpResponse('OK')


def template_response(request):
    return TemplateResponse(request, Template('OK'))


def template_response_error(request):
    return TemplateResponse(request, Template('{%'))


def not_found(request):
    raise http.Http404()


def server_error(request):
    raise Exception('Error in view')


def null_view(request):
    return None


def permission_denied(request):
    raise PermissionDenied()
