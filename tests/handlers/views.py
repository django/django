from __future__ import unicode_literals

from django.db import connection
from django.http import HttpResponse, StreamingHttpResponse

def regular(request):
    return HttpResponse(b"regular content")

def streaming(request):
    return StreamingHttpResponse([b"streaming", b" ", b"content"])

def in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))

def not_in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))
not_in_transaction.transactions_per_request = False
