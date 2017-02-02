from django.apps import apps


def get_current_site(request):
    """
    Checks if contrib.sites is installed and returns either the current
    ``Site`` object or a ``RequestSite`` object based on the request.
    """
    # Imports are inside the function because its point is to avoid importing
    # the Site models when django.contrib.sites isn't installed.
    if apps.is_installed('django.contrib.sites'):
        from .models import Site
        return Site.objects.get_current(request)
    else:
        from .requests import RequestSite
        return RequestSite(request)
