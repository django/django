from __future__ import unicode_literals

from django.utils.encoding import escape_uri_path, escape_query_string, iri_to_uri
from django.utils.six.moves.urllib.parse import urlsplit, urljoin, urlunsplit


def resolve_dot_segments(path):
    # Split path into segments.
    segments = path.split('/')
    # Remove all single dots except for the last segment.
    segments = [s for s in segments[:-1] if s != '.'] + segments[-1:]
    # Remove all leading double dots. Remove all other double dots and their
    # preceding segments.
    while '..' in segments[:-1]:
        index = segments.index('..')
        if index == 1:
            segments[1:2] = []
        else:
            segments[index-1:index+1] = []
    # If the last segment is a single dot, replace it with an empty segment.
    if segments and segments[-1] == '.':
        segments[-1:] = ['']
    # If the last segment is a double dot, replace the last two segments with
    # a single empty segment.
    if segments and segments[-1] == '..':
        segments[-2:] = ['']
    return '/'.join(segments)


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
            escape_uri_path(self.path) or '/',
            escape_query_string(self.query_string),
            iri_to_uri(self.fragment)
        )))

    def copy(self):
        return type(self)(
            self.scheme, self.host, self.path,
            self.query_string, self.fragment
        )
