from __future__ import unicode_literals

from django.core.exceptions import SuspiciousOperation
from django.db import connection, transaction
from django.http import HttpResponse, StreamingHttpResponse

def regular(request):
    return HttpResponse(b"regular content")

def streaming(request):
    return StreamingHttpResponse([b"streaming", b" ", b"content"])

def in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))

@transaction.non_atomic_requests
def not_in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))

def suspicious(request):
    raise SuspiciousOperation('dubious')
