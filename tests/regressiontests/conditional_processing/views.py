# -*- coding:utf-8 -*-
from django.views.decorators.http import condition
from django.http import HttpResponse

from models import FULL_RESPONSE, LAST_MODIFIED, ETAG

@condition(lambda r: ETAG, lambda r: LAST_MODIFIED)
def index(request):
    return HttpResponse(FULL_RESPONSE)

@condition(last_modified_func=lambda r: LAST_MODIFIED)
def last_modified(request):
    return HttpResponse(FULL_RESPONSE)

@condition(etag_func=lambda r: ETAG)
def etag(request):
    return HttpResponse(FULL_RESPONSE)
