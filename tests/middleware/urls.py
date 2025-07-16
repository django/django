from django.urls import path, re_path
from django.views.debug import default_urlconf

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
    path("csp-failure/", default_urlconf),
    path("csp-report/", views.csp_report_view),
    path("csp-base/", views.empty_view),
    path("csp-nonce/", views.csp_nonce),
    path("csp-500/", views.csp_500),
]
