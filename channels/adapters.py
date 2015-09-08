import functools

from django.core.handlers.base import BaseHandler
from django.http import HttpRequest, HttpResponse

from channels import Channel


class UrlConsumer(object):
    """
    Dispatches channel HTTP requests into django's URL system.
    """

    def __init__(self):
        self.handler = BaseHandler()
        self.handler.load_middleware()

    def __call__(self, message):
        request = HttpRequest.channel_decode(message.content)
        try:
            response = self.handler.get_response(request)
        except HttpResponse.ResponseLater:
            return
        message.reply_channel.send(response.channel_encode())


def view_producer(channel_name):
    """
    Returns a new view function that actually writes the request to a channel
    and abandons the response (with an exception the Worker will catch)
    """
    def producing_view(request):
        Channel(channel_name).send(request.channel_encode())
        raise HttpResponse.ResponseLater()
    return producing_view


def view_consumer(func):
    """
    Decorates a normal Django view to be a channel consumer.
    Does not run any middleware
    """
    @functools.wraps(func)
    def consumer(message):
        request = HttpRequest.channel_decode(message.content)
        response = func(request)
        message.reply_channel.send(response.channel_encode())
    return func
