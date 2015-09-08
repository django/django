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
        "GET": dict(request.GET.lists()),
        "POST": dict(request.POST.lists()),
        "COOKIES": request.COOKIES,
        "META": {k: v for k, v in request.META.items() if not k.startswith("wsgi")},
        "path": request.path,
        "path_info": request.path_info,
        "method": request.method,
        "reply_channel": request.reply_channel,
    }
    return value


def decode_request(value):
    """
    Decodes a request JSONish value to a HttpRequest object.
    """
    request = HttpRequest()
    request.GET = CustomQueryDict(value['GET'])
    request.POST = CustomQueryDict(value['POST'])
    request.COOKIES = value['COOKIES']
    request.META = value['META']
    request.path = value['path']
    request.method = value['method']
    request.path_info = value['path_info']
    request.reply_channel = value['reply_channel']
    return request


class CustomQueryDict(QueryDict):
    """
    Custom override of QueryDict that sets things directly.
    """

    def __init__(self, values):
        MultiValueDict.__init__(self, values)
