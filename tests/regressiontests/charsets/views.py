from django.http import HttpResponse
from django.shortcuts import render_to_response

def accept_charset(request):
    return HttpResponse("ASCII.", origin_request=request)

def good_content_type(request):
    return HttpResponse("ASCII.", content_type="text/html; charset=us")

def bad_content_type(request):
    return HttpResponse("ASCII.", content_type="text/html; charset=this_should_be_junk")
