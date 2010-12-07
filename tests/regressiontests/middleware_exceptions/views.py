from django import http
from django.core.exceptions import PermissionDenied
from django.template import Template
from django.template.response import TemplateResponse


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
