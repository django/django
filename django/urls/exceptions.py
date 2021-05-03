from django.http import Http404


class Resolver404(Http404):
    pass


class NoReverseMatch(Exception):
    pass


class DoesNotResolve(Resolver404):
    pass