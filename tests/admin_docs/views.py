from freedom.http import HttpResponse
from freedom.utils.decorators import decorator_from_middleware
from freedom.views.generic import View
from freedom.contrib.admindocs.middleware import XViewMiddleware

xview_dec = decorator_from_middleware(XViewMiddleware)


def xview(request):
    return HttpResponse()


class XViewClass(View):
    def get(self, request):
        return HttpResponse()
