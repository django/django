from django.core.handlers.base import BaseHandler
from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from .request import decode_request, encode_request
from .response import ResponseLater, decode_response, encode_response


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
    # Ensure that the staticfiles version of runserver bows down to us
    # This one is particularly horrible
    from django.contrib.staticfiles.management.commands.runserver import Command as StaticRunserverCommand
    from .management.commands.runserver import Command as RunserverCommand
    StaticRunserverCommand.__bases__ = (RunserverCommand, )


def new_handle_uncaught_exception(self, request, resolver, exc_info):
    if exc_info[0] is ResponseLater:
        raise
    return BaseHandler.old_handle_uncaught_exception(self, request, resolver, exc_info)
