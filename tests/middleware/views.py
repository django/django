import sys

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.debug import technical_500_response
from django.views.decorators.common import no_append_slash
from django.views.generic import View


def empty_view(request, *args, **kwargs):
    return HttpResponse()


@no_append_slash
def sensitive_fbv(request, *args, **kwargs):
    return HttpResponse()


@method_decorator(no_append_slash, name="dispatch")
class SensitiveCBV(View):
    def get(self, *args, **kwargs):
        return HttpResponse()


def csp_nonce(request):
    return HttpResponse(request.csp_nonce)


def csp_500(request):
    try:
        raise Exception
    except Exception:
        return technical_500_response(request, *sys.exc_info())
