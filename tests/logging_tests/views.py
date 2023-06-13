from django.core.exceptions import DisallowedHost, PermissionDenied, SuspiciousOperation
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.http.multipartparser import MultiPartParserError


def innocent(request):
    return HttpResponse("innocent")


def redirect(request):
    return HttpResponseRedirect("/")


def suspicious(request):
    raise SuspiciousOperation("dubious")


def suspicious_spec(request):
    raise DisallowedHost("dubious")


class UncaughtException(Exception):
    pass


def uncaught_exception(request):
    raise UncaughtException("Uncaught exception")


def internal_server_error(request):
    status = request.GET.get("status", 500)
    return HttpResponseServerError("Server Error", status=int(status))


def permission_denied(request):
    raise PermissionDenied()


def multi_part_parser_error(request):
    raise MultiPartParserError("parsing error")


def does_not_exist_raised(request):
    raise Http404("Not Found")
