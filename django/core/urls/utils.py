from __future__ import unicode_literals

from django.utils.encoding import escape_query_string, iri_to_uri
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit


def resolve_error_handler(urlconf, view_type):
    callback = getattr(urlconf, 'handler%s' % view_type, None)
    if not callback:
        # No handler specified in file; use default
        # Lazy import, since django.urls imports this file
        from django.conf import urls
        callback = getattr(urls, 'handler%s' % view_type)
    from django.core.urlresolvers import get_callable
    return get_callable(callback), {}


class URL(object):
    def __init__(self, scheme='', host='', path='', query_string='', fragment=''):
        self.scheme = scheme
        self.host = host
        self.path = path
        self.query_string = query_string
        self.fragment = fragment

    @classmethod
    def from_location(cls, location):
        return cls(*urlsplit(location))

    @classmethod
    def from_request(cls, request):
        return cls(
            request.scheme,
            request.get_host(),
            request.path,
            request.META.get('QUERY_STRING', ''),
            ''
        )

    def __repr__(self):
        return "<URL '%s'>" % urlunsplit((self.scheme, self.host, self.path, self.query_string, self.fragment))

    def __str__(self):
        return iri_to_uri(urlunsplit((
            self.scheme,
            self.host,
            self.path or '/',
            escape_query_string(self.query_string),
            self.fragment
        )))

    def copy(self):
        return type(self)(
            self.scheme, self.host, self.path,
            self.query_string, self.fragment
        )
