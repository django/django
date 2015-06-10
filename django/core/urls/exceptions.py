from __future__ import unicode_literals

from django.http import Http404


class Resolver404(Http404):
    """
    Raised when an url cannot be resolved to a view.
    """
    pass


class NoReverseMatch(Exception):
    """
    Raised when reverse() cannot reconstruct a valid url.
    """
    pass
