from django.contrib.admindocs.middleware import XViewMiddleware
from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware
from django.views.generic import View

xview_dec = decorator_from_middleware(XViewMiddleware)


def xview(request):
    return HttpResponse()


class XViewClass(View):
    def get(self, request):
        return HttpResponse()


class XViewCallableObject(View):
    def __call__(self, request):
        return HttpResponse()


class CompanyView(View):
    """
    This is a view for :model:`myapp.Company`
    """

    def get(self, request):
        return HttpResponse()
