from __future__ import unicode_literals

from django.core.exceptions import DisallowedHost, SuspiciousOperation


def suspicious(request):
    raise SuspiciousOperation('dubious')


def suspicious_spec(request):
    raise DisallowedHost('dubious')
