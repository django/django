from functools import cache

from django.contrib.sites.shortcuts import get_current_site


def site(request) -> dict:
    """Returns a context variable with the current site."""

    @cache
    def current_site():
        return get_current_site(request)

    return {"site": current_site}
