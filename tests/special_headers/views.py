from django.core.xheaders import populate_xheaders
from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware
from django.views.generic import View
from django.middleware.doc import XViewMiddleware

from .models import Article

xview_dec = decorator_from_middleware(XViewMiddleware)

def xview(request):
    return HttpResponse()

def xview_xheaders(request, object_id):
    response = HttpResponse()
    populate_xheaders(request, response, Article, 1)
    return response

class XViewClass(View):
    def get(self, request):
        return HttpResponse()
