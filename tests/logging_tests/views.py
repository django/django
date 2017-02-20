from django.core.exceptions import DisallowedHost, SuspiciousOperation
from django.http import HttpResponse


def innocent(request):
    return HttpResponse('innocent')


def suspicious(request):
    raise SuspiciousOperation('dubious')


def suspicious_spec(request):
    raise DisallowedHost('dubious')
