from thibaud.contrib.admindocs.middleware import XViewMiddleware
from thibaud.http import HttpResponse
from thibaud.utils.decorators import decorator_from_middleware
from thibaud.views.generic import View

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
