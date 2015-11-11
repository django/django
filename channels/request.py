from django.http import HttpRequest
from django.http.request import QueryDict
from django.utils.datastructures import MultiValueDict


def encode_request(request):
    """
    Encodes a request to JSON-compatible datastructures
    """
    # TODO: More stuff
    value = {
        "get": dict(request.GET.lists()),
        "post": dict(request.POST.lists()),
        "cookies": request.COOKIES,
        "headers": {
            k[5:].lower(): v
            for k, v in request.META.items()
            if k.lower().startswith("http_")
        },
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
    request.path = value['path']
    request.method = value['method']
    request.reply_channel = value['reply_channel']
    # Channels requests are more high-level than the dumping ground that is
    # META; re-combine back into it
    request.META = {
        "REQUEST_METHOD": value["method"],
        "SERVER_NAME": value["server"][0],
        "SERVER_PORT": value["server"][1],
        "REMOTE_ADDR": value["client"][0],
        "REMOTE_HOST": value["client"][0],  # Not the DNS name, hopefully fine.
    }
    for header, header_value in value.get("headers", {}).items():
        request.META["HTTP_%s" % header.upper()] = header_value
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
