from __future__ import unicode_literals

from django.http import Http404


class Resolver404(Http404):
    pass


class NoReverseMatch(Exception):
    pass
