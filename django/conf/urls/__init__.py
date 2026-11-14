from django.urls import include
from django.views import defaults

__all__ = [
    "handler400",
    "handler403",
    "handler404",
    "handler413",
    "handler500",
    "include",
]

handler400 = defaults.bad_request
handler403 = defaults.permission_denied
handler404 = defaults.page_not_found
handler413 = defaults.content_too_large
handler500 = defaults.server_error
