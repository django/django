from django.contrib.sites.shortcuts import get_current_site


def site(request):
    """Returns a context variable with the current site."""
    return {"site": get_current_site(request)}
