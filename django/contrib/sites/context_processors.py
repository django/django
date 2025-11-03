from django.utils.functional import SimpleLazyObject
from django.contrib.sites.shortcuts import get_current_site


def site(request) -> dict:
    """Returns a context variable with the current site."""

    return {"site": SimpleLazyObject(lambda: get_current_site(request))}
