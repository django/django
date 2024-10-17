from django.http import HttpResponse
from django.middleware import csp
from django.utils.decorators import method_decorator
from django.views.decorators.common import no_append_slash
from django.views.decorators.csp import csp_enforced, csp_exempt, csp_report_only
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


@csp_exempt(enforced=True)
def csp_exempt_view(request):
    return HttpResponse()


@csp_exempt(report_only=True)
def csp_exempt_ro_view(request):
    return HttpResponse()


@csp_exempt(enforced=True, report_only=True)
def csp_exempt_both_view(request):
    return HttpResponse()


csp_policy_override = {
    "DIRECTIVES": {
        "default-src": [csp.SELF],
        "img-src": [csp.SELF, "data:"],
    }
}


@csp_enforced(csp_policy_override)
def override_csp_enforced(request):
    return HttpResponse()


@csp_report_only(csp_policy_override)
def override_csp_report_only(request):
    return HttpResponse()


@csp_enforced(csp_policy_override)
@csp_report_only(csp_policy_override)
def override_csp_both(request):
    return HttpResponse()
