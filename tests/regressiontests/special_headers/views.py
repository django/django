# -*- coding:utf-8 -*-
from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware
from django.views.generic import View
from django.middleware.doc import XViewMiddleware

xview_dec = decorator_from_middleware(XViewMiddleware)

def xview(request):
    return HttpResponse()

class XViewClass(View):
    def get(self, request):
        return HttpResponse()
