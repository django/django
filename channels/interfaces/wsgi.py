import django
from django.core.handlers.wsgi import WSGIHandler
from django.http import HttpResponse
from channels import Channel


class WSGIInterface(WSGIHandler):
    """
    WSGI application that pushes requests to channels.
    """

    def __init__(self, channel_backend, *args, **kwargs):
        self.channel_backend = channel_backend
        django.setup()
        super(WSGIInterface, self).__init__(*args, **kwargs)

    def get_response(self, request):
        request.response_channel = Channel.new_name("django.wsgi.response")
        Channel("django.wsgi.request", channel_backend=self.channel_backend).send(**request.channel_encode())
        channel, message = self.channel_backend.receive_many_blocking([request.response_channel])
        return HttpResponse.channel_decode(message)
