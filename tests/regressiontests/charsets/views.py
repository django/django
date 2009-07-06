from django.http import HttpResponse
from django.shortcuts import render_to_response

def accept_charset(request):
    return HttpResponse("ASCII.", request=request)

def good_content_type(request):
    return HttpResponse("ASCII.", content_type="text/html; charset=us")

def bad_content_type(request):
    return HttpResponse("UTF-8", content_type="text/html; charset=this_should_be_junk")

def content_type_no_charset(request):
    return HttpResponse("UTF-8", content_type="text/html")

def encode_response(request):
    return HttpResponse(u"\ue863", content_type="text/html; charset=GBK")

def basic_response(request):
    return HttpResponse("ASCII.")
