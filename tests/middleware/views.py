import json
import sys

from django.http import HttpResponse
from django.middleware.csp import get_nonce
from django.utils.decorators import method_decorator
from django.views.debug import technical_500_response
from django.views.decorators.common import no_append_slash
from django.views.decorators.csrf import csrf_exempt
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
    return HttpResponse(get_nonce(request))


def csp_500(request):
    try:
        raise Exception
    except Exception:
        return technical_500_response(request, *sys.exc_info())


csp_reports = []


@csrf_exempt
def csp_report_view(request):
    if request.method == "POST":
        data = json.loads(request.body)
        csp_reports.append(data)
    return HttpResponse(status=204)
