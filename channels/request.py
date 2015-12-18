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
        "root_path": request.META.get("SCRIPT_NAME", ""),
        "method": request.method,
        "reply_channel": request.reply_channel,
        "server": [
            request.META.get("SERVER_NAME", None),
            request.META.get("SERVER_PORT", None),
        ],
        "client": [
            request.META.get("REMOTE_ADDR", None),
            request.META.get("REMOTE_PORT", None),
        ],
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
        "SCRIPT_NAME": value["root_path"],
    }
    for header, header_value in value.get("headers", {}).items():
        request.META["HTTP_%s" % header.upper()] = header_value
    # Derive path_info from script root
    request.path_info = request.path
    if request.META.get("SCRIPT_NAME", ""):
        request.path_info = request.path_info[len(request.META["SCRIPT_NAME"]):]
    return request


class CustomQueryDict(QueryDict):
    """
    Custom override of QueryDict that sets things directly.
    """

    def __init__(self, values, mutable=False, encoding=None):
        """ mutable and encoding are ignored :( """
        MultiValueDict.__init__(self, values)
