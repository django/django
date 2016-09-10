from django.http import HttpResponse
from django.views.decorators.http import condition, etag, last_modified

from .tests import ETAG, FULL_RESPONSE, LAST_MODIFIED


def index(request):
    return HttpResponse(FULL_RESPONSE)
index = condition(lambda r: ETAG, lambda r: LAST_MODIFIED)(index)


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


def etag_view_unquoted(request):
    """
    Use an etag_func() that returns an unquoted ETag.
    """
    return HttpResponse(FULL_RESPONSE)
etag_view_unquoted = condition(etag_func=lambda r: ETAG.strip('"'))(etag_view_unquoted)


def etag_view_none(request):
    """
    Use an etag_func() that returns None (as distinct from setting etag_func
    itself to None).
    """
    return HttpResponse(FULL_RESPONSE)
etag_view_none = condition(etag_func=lambda r: None)(etag_view_none)
