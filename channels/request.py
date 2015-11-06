from django.http import HttpRequest
from django.utils.datastructures import MultiValueDict
from django.http.request import QueryDict
from django.conf import settings


def encode_request(request):
    """
    Encodes a request to JSON-compatible datastructures
    """
    # TODO: More stuff
    value = {
        "get": dict(request.GET.lists()),
        "post": dict(request.POST.lists()),
        "cookies": request.COOKIES,
        "meta": {k: v for k, v in request.META.items() if not k.startswith("wsgi")},
        "path": request.path,
        "method": request.method,
        "reply_channel": request.reply_channel,
    }
    return value


def decode_request(value):
    """
    Decodes a request JSONish value to a HttpRequest object.
    """
    request = HttpRequest()
    request.GET = CustomQueryDict(value['get'])
    request.POST = CustomQueryDict(value['post'])
    request.COOKIES = value['cookies']
    request.META = value['meta']
    request.path = value['path']
    request.method = value['method']
    request.reply_channel = value['reply_channel']
    # We don't support non-/ script roots
    request.path_info = value['path']
    return request


class CustomQueryDict(QueryDict):
    """
    Custom override of QueryDict that sets things directly.
    """

    def __init__(self, values, mutable=False, encoding=None):
        """ mutable and encoding are ignored :( """
        MultiValueDict.__init__(self, values)
