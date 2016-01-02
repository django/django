from __future__ import unicode_literals

from django.http import Http404


class Resolver404(Http404):
    """
    Raised when an url cannot be resolved to a view.
    """
    @property
    def path(self):
        if self.args:
            return self.args[0].get('path', '')
        return ''

    @property
    def tried(self):
        if self.args:
            return self.args[0].get('tried', [])
        return []


class NoReverseMatch(Exception):
    """
    Raised when reverse() cannot reconstruct a valid url.
    """
    pass
