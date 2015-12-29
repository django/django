from __future__ import unicode_literals

from django.http import Http404


class Resolver404(Http404):
    """
    Raised when an url cannot be resolved to a view.
    """
    def __init__(self, path=None, tried=None):
        self.path = path
        self.tried = tried or []


class NoReverseMatch(Exception):
    """
    Raised when reverse() cannot reconstruct a valid url.
    """
    pass
