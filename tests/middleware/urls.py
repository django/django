from django.urls import path, re_path

from . import views

urlpatterns = [
    path("noslash", views.empty_view),
    path("slash/", views.empty_view),
    path("needsquoting#/", views.empty_view),
    # Accepts paths with two leading slashes.
    re_path(r"^(.+)/security/$", views.empty_view),
    # Should not append slash.
    path("sensitive_fbv/", views.sensitive_fbv),
    path("sensitive_cbv/", views.SensitiveCBV.as_view()),
    # Used in CSP tests.
    path("csp-base/", views.empty_view),
    path("csp-nonce/", views.csp_nonce),
    path("csp-exempt/", views.csp_exempt_view),
    path("csp-exempt-report-only/", views.csp_exempt_ro_view),
    path("csp-exempt-both/", views.csp_exempt_both_view),
    path("override-csp-enforced/", views.override_csp_enforced),
    path("override-csp-report-only/", views.override_csp_report_only),
    path("override-csp-both/", views.override_csp_both),
]
