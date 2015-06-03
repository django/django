from django.core.handlers.base import BaseHandler
from channel import Channel
from .response import encode_response
from .request import decode_request


class DjangoUrlAdapter(object):
    """
    Adapts the channel-style HTTP requests to the URL-router/handler style
    """

    def __init__(self):
        self.handler = BaseHandler()
        self.handler.load_middleware()

    def __call__(self, request, response_channel):
        response = self.handler.get_response(decode_request(request))
        Channel(response_channel).send(**encode_response(response))
