import functools

from django.http import HttpRequest, HttpResponse
from channels import Channel


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
