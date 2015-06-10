from django.http.request import HttpRequest
from django.http.response import HttpResponseBase
from django.core.handlers.base import BaseHandler
from .request import encode_request, decode_request
from .response import encode_response, decode_response, ResponseLater


def monkeypatch_django():
    """
    Monkeypatches support for us into parts of Django.
    """
    # Request encode/decode
    HttpRequest.channel_encode = encode_request
    HttpRequest.channel_decode = staticmethod(decode_request)
    # Response encode/decode
    HttpResponseBase.channel_encode = encode_response
    HttpResponseBase.channel_decode = staticmethod(decode_response)
    HttpResponseBase.ResponseLater = ResponseLater
    # Allow ResponseLater to propagate above handler
    BaseHandler.old_handle_uncaught_exception = BaseHandler.handle_uncaught_exception
    BaseHandler.handle_uncaught_exception = new_handle_uncaught_exception


def new_handle_uncaught_exception(self, request, resolver, exc_info):
    if exc_info[0] is ResponseLater:
        raise
    return BaseHandler.old_handle_uncaught_exception(self, request, resolver, exc_info)
