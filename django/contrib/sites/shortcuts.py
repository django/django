from django.apps import apps

from .requests import RequestSite


def get_current_site(request):
    """
    Check if contrib.sites is installed and return either the current
    ``Site`` object or a ``RequestSite`` object based on the request.
    """
    # Import is inside the function because its point is to avoid importing the
    # Site models when django.contrib.sites isn't installed.
    if apps.is_installed("django.contrib.sites"):
        from .models import Site

        return Site.objects.get_current(request)
    else:
        return RequestSite(request)
