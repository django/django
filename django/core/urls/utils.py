from __future__ import unicode_literals

from django.utils.encoding import escape_uri_path, escape_query_string, iri_to_uri
from django.utils.six.moves.urllib.parse import urlsplit, urlunsplit


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
        return urlunsplit((
            self.scheme,
            self.host,
            escape_uri_path(self.path) or '/',
            escape_query_string(self.query_string),
            iri_to_uri(self.fragment)
        ))

    def copy(self):
        return type(self)(
            self.scheme, self.host, self.path,
            self.query_string, self.fragment
        )
