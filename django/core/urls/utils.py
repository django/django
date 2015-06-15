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
        # scheme and host are case-insensitive according to
        # RFC 3986 section 3.1 and 3.2.2. Normalize these now.
        self.scheme = scheme.lower()
        self.host = host.lower()
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
        return self.get_full_path()

    def get_full_path(self, force_append_slash=False):
        return '%s%s%s%s' % (
            escape_uri_path(self.path) or '/',
            '/' if force_append_slash and not self.path.endswith('/') else '',
            ('?' + escape_query_string(self.query_string)) if self.query_string else '',
            ('#' + iri_to_uri(self.fragment)) if self.fragment else '',
        )

    def build_absolute_path(self, location):
        """
        Build an absolute URL path for location, relative to current location.
        """
        if not location:
            path = self.path
        elif location.startswith('/'):
            path = location
        else:
            path = '%s/%s' % (self.path.rsplit('/', 1)[0], location)
        return resolve_dot_segments(path) or '/'

    def build_relative_url(self, location=None):
        """
        Build a URL for location, relative to the current location. May be
        scheme- and host-relative for same-domain URLs, but always build an
        absolute path.
        """
        if location is None:
            return self.get_full_path()
        if isinstance(location, URL):
            location = location.build_absolute_url()
        bits = urlsplit(location)
        set_scheme = not (bits.scheme == self.scheme or not bits.scheme)
        set_host = not (bits.netloc.lower() == self.host or not bits.netloc)
        if not set_scheme and not set_host:
            return self.build_absolute_path(location)
        if not set_scheme:
            current_uri = '//{host}{path}'.format(self.host, self.path)
        else:
            current_uri = '{scheme}://{host}{path}'.format(self.scheme, self.host, self.path)
        return urljoin(current_uri, location)

    def build_absolute_url(self, location=None):
        """
        Builds an absolute URI from the location and the variables available in
        this request. If no ``location`` is specified, the absolute URI is
        built on ``request.get_full_path()``. Anyway, if the location is
        absolute, it is simply converted to an RFC 3987 compliant URI and
        returned and if location is relative or is scheme-relative (i.e.,
        ``//example.com/``), it is urljoined to a base URL constructed from the
        request variables.
        """
        if location is None:
            # Make it an absolute url (but schemeless and domainless) for the
            # edge case that the path starts with '//'.
            location = '//%s' % self.get_full_path()
        bits = urlsplit(location)
        if not (bits.scheme and bits.netloc):
            current_uri = '{scheme}://{host}{path}'.format(scheme=self.scheme,
                                                           host=self.host,
                                                           path=self.path)
            # Join the constructed URL with the provided location, which will
            # allow the provided ``location`` to apply query strings to the
            # base path as well as override the host, if it begins with //
            location = urljoin(current_uri, location)
        return location

    def copy(self):
        return type(self)(
            self.scheme, self.host, self.path,
            self.query_string, self.fragment
        )
