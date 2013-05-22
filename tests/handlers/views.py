from __future__ import unicode_literals

from django.db import connection, transaction
from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.predicate import url_predicates

def regular(request):
    return HttpResponse(b"regular content")

def streaming(request):
    return StreamingHttpResponse([b"streaming", b" ", b"content"])

def in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))

@transaction.non_atomic_requests
def not_in_transaction(request):
    return HttpResponse(str(connection.in_atomic_block))

@url_predicates([lambda request: request.method == 'POST',])
def predicate(request):
    return HttpResponse(b"predicate content")
