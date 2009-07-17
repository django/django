import codecs
from django.http import HttpResponse
from django.shortcuts import render_to_response

test_string = u'\u82cf\u8054\u961f'
codec = "GBK"

def accept_charset(request):
    return HttpResponse("ASCII.", request=request)

def good_content_type(request):
    return HttpResponse("ASCII.", content_type="text/html; charset=us")

def bad_content_type(request):
    return HttpResponse("UTF-8", content_type="text/html; charset=this_should_be_junk")

def content_type_no_charset(request):
    return HttpResponse("UTF-8", content_type="text/html")

def encode_response_content_type(request):
    return HttpResponse(test_string, content_type="text/html; charset=GBK")

def encode_response_accept_charset(request):
    return HttpResponse(test_string, request=request)

def basic_response(request):
    return HttpResponse("ASCII.")

# This mimics codecs.CodecInfo enough for the purposes of HttpResponse.
class FakeCodec:
    def __init__(self, name=None):
        if name:
            self.name = name

def bad_codec(request):
    data = HttpResponse("ASCII.")
    data.codec = FakeCodec()
    return data

def good_codec(request):
    data = HttpResponse(test_string)
    data.codec = FakeCodec(codec)
    return data
