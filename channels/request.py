from django.http import HttpRequest
from django.utils.datastructures import MultiValueDict


def encode_request(request):
    """
    Encodes a request to JSON-compatible datastructures
    """
    # TODO: More stuff
    value = {
        "GET": list(request.GET.items()),
        "POST": list(request.POST.items()),
        "COOKIES": request.COOKIES,
        "META": {k: v for k, v in request.META.items() if not k.startswith("wsgi")},
        "path": request.path,
        "path_info": request.path_info,
        "method": request.method,
        "response_channel": request.response_channel,
    }
    return value


def decode_request(value):
    """
    Decodes a request JSONish value to a HttpRequest object.
    """
    request = HttpRequest()
    request.GET = MultiValueDict(value['GET'])
    request.POST = MultiValueDict(value['POST'])
    request.COOKIES = value['COOKIES']
    request.META = value['META']
    request.path = value['path']
    request.method = value['method']
    request.path_info = value['path_info']
    request.response_channel = value['response_channel']
    return request
