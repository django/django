import sys

from django.http import HttpResponse
from django.middleware.constants import CSP
from django.utils.decorators import method_decorator
from django.views.debug import technical_500_response
from django.views.decorators.common import no_append_slash
from django.views.decorators.csp import csp_disabled, csp_override
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


@csp_disabled
def csp_disabled_both(request):
    return HttpResponse()


@csp_disabled(report_only=False)
def csp_disabled_enforced(request):
    return HttpResponse()


@csp_disabled(enforced=False)
def csp_disabled_ro(request):
    return HttpResponse()


csp_policy_override = {
    "DIRECTIVES": {
        "default-src": [CSP.SELF],
        "img-src": [CSP.SELF, "data:"],
    }
}


@csp_override(csp_policy_override)
def override_csp_both(request):
    return HttpResponse()


@csp_override(csp_policy_override, report_only=False)
def override_csp_enforced(request):
    return HttpResponse()


@csp_override(csp_policy_override, enforced=False)
def override_csp_report_only(request):
    return HttpResponse()


def csp_500(request):
    try:
        raise Exception
    except Exception:
        return technical_500_response(request, *sys.exc_info())
