from django.contrib.sites.shortcuts import get_current_site


def site(request):
    """Context processor that returns current site"""
    return {"site": get_current_site(request)}
