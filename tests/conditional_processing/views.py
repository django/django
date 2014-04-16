from django.views.decorators.http import condition, etag, last_modified
from django.http import HttpResponse

from .tests import FULL_RESPONSE, LAST_MODIFIED, ETAG, MODIFIED_RESPONSE, LAST_MODIFIED_NEWER, EXPIRED_ETAG

def last_modified_func(request):
    return LAST_MODIFIED_NEWER if getattr(request,'modified',False) else LAST_MODIFIED

def etag_func(request):
    return EXPIRED_ETAG if getattr(request,'modified',False) else ETAG

def index_func(request):
    request.modified = request.method == 'PUT'
    return HttpResponse(MODIFIED_RESPONSE if request.modified else FULL_RESPONSE)
index = condition(etag_func, last_modified_func)(index_func)
index_static = condition(etag_func, last_modified_func,update=())(index_func)


def last_modified_view1(request):
    return HttpResponse(FULL_RESPONSE)
last_modified_view1 = condition(last_modified_func=lambda r: LAST_MODIFIED)(last_modified_view1)


def last_modified_view2(request):
    return HttpResponse(FULL_RESPONSE)
last_modified_view2 = last_modified(lambda r: LAST_MODIFIED)(last_modified_view2)


def etag_view1(request):
    return HttpResponse(FULL_RESPONSE)
etag_view1 = condition(etag_func=lambda r: ETAG)(etag_view1)


def etag_view2(request):
    return HttpResponse(FULL_RESPONSE)
etag_view2 = etag(lambda r: ETAG)(etag_view2)
