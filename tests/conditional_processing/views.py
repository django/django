from django.http import HttpResponse
from django.views.decorators.http import condition, etag, last_modified

from .tests import ETAG, FULL_RESPONSE, LAST_MODIFIED, WEAK_ETAG


@condition(lambda r: ETAG, lambda r: LAST_MODIFIED)
def index(request):
    return HttpResponse(FULL_RESPONSE)


@condition(last_modified_func=lambda r: LAST_MODIFIED)
def last_modified_view1(request):
    return HttpResponse(FULL_RESPONSE)


@last_modified(lambda r: LAST_MODIFIED)
def last_modified_view2(request):
    return HttpResponse(FULL_RESPONSE)


@condition(etag_func=lambda r: ETAG)
def etag_view1(request):
    return HttpResponse(FULL_RESPONSE)


@etag(lambda r: ETAG)
def etag_view2(request):
    return HttpResponse(FULL_RESPONSE)


@condition(etag_func=lambda r: ETAG.strip('"'))
def etag_view_unquoted(request):
    """
    Use an etag_func() that returns an unquoted ETag.
    """
    return HttpResponse(FULL_RESPONSE)


@condition(etag_func=lambda r: WEAK_ETAG)
def etag_view_weak(request):
    """
    Use an etag_func() that returns a weak ETag.
    """
    return HttpResponse(FULL_RESPONSE)


@condition(etag_func=lambda r: None)
def etag_view_none(request):
    """
    Use an etag_func() that returns None, as opposed to setting etag_func=None.
    """
    return HttpResponse(FULL_RESPONSE)
