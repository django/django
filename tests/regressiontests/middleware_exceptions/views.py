from django import http
from django.core.exceptions import PermissionDenied

def normal_view(request):
    return http.HttpResponse('OK')

def not_found(request):
    raise http.Http404()

def server_error(request):
    raise Exception('Error in view')

def null_view(request):
    return None

def permission_denied(request):
    raise PermissionDenied()
