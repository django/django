# -*- coding: utf-8 -*-
# Copyright (c) 2015 Ian Stapleton Cordasco
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module containing the urlparse compatibility logic."""
from collections import namedtuple

from . import compat
from . import exceptions
from . import misc
from . import normalizers
from . import uri

__all__ = ('ParseResult', 'ParseResultBytes')

PARSED_COMPONENTS = ('scheme', 'userinfo', 'host', 'port', 'path', 'query',
                     'fragment')


class ParseResultMixin(object):
    def _generate_authority(self, attributes):
        # I swear I did not align the comparisons below. That's just how they
        # happened to align based on pep8 and attribute lengths.
        userinfo, host, port = (attributes[p]
                                for p in ('userinfo', 'host', 'port'))
        if (self.userinfo != userinfo or
                self.host != host or
                self.port != port):
            if port:
                port = '{0}'.format(port)
            return normalizers.normalize_authority(
                (compat.to_str(userinfo, self.encoding),
                 compat.to_str(host, self.encoding),
                 port)
            )
        return self.authority

    def geturl(self):
        """Shim to match the standard library method."""
        return self.unsplit()

    @property
    def hostname(self):
        """Shim to match the standard library."""
        return self.host

    @property
    def netloc(self):
        """Shim to match the standard library."""
        return self.authority

    @property
    def params(self):
        """Shim to match the standard library."""
        return self.query


class ParseResult(namedtuple('ParseResult', PARSED_COMPONENTS),
                  ParseResultMixin):
    """Implementation of urlparse compatibility class.

    This uses the URIReference logic to handle compatibility with the
    urlparse.ParseResult class.
    """

    slots = ()

    def __new__(cls, scheme, userinfo, host, port, path, query, fragment,
                uri_ref, encoding='utf-8'):
        """Create a new ParseResult."""
        parse_result = super(ParseResult, cls).__new__(
            cls,
            scheme or None,
            userinfo or None,
            host,
            port or None,
            path or None,
            query,
            fragment)
        parse_result.encoding = encoding
        parse_result.reference = uri_ref
        return parse_result

    @classmethod
    def from_parts(cls, scheme=None, userinfo=None, host=None, port=None,
                   path=None, query=None, fragment=None, encoding='utf-8'):
        """Create a ParseResult instance from its parts."""
        authority = ''
        if userinfo is not None:
            authority += userinfo + '@'
        if host is not None:
            authority += host
        if port is not None:
            authority += ':{0}'.format(port)
        uri_ref = uri.URIReference(scheme=scheme,
                                   authority=authority,
                                   path=path,
                                   query=query,
                                   fragment=fragment,
                                   encoding=encoding).normalize()
        userinfo, host, port = authority_from(uri_ref, strict=True)
        return cls(scheme=uri_ref.scheme,
                   userinfo=userinfo,
                   host=host,
                   port=port,
                   path=uri_ref.path,
                   query=uri_ref.query,
                   fragment=uri_ref.fragment,
                   uri_ref=uri_ref,
                   encoding=encoding)

    @classmethod
    def from_string(cls, uri_string, encoding='utf-8', strict=True,
                    lazy_normalize=True):
        """Parse a URI from the given unicode URI string.

        :param str uri_string: Unicode URI to be parsed into a reference.
        :param str encoding: The encoding of the string provided
        :param bool strict: Parse strictly according to :rfc:`3986` if True.
            If False, parse similarly to the standard library's urlparse
            function.
        :returns: :class:`ParseResult` or subclass thereof
        """
        reference = uri.URIReference.from_string(uri_string, encoding)
        if not lazy_normalize:
            reference = reference.normalize()
        userinfo, host, port = authority_from(reference, strict)

        return cls(scheme=reference.scheme,
                   userinfo=userinfo,
                   host=host,
                   port=port,
                   path=reference.path,
                   query=reference.query,
                   fragment=reference.fragment,
                   uri_ref=reference,
                   encoding=encoding)

    @property
    def authority(self):
        """Return the normalized authority."""
        return self.reference.authority

    def copy_with(self, scheme=misc.UseExisting, userinfo=misc.UseExisting,
                  host=misc.UseExisting, port=misc.UseExisting,
                  path=misc.UseExisting, query=misc.UseExisting,
                  fragment=misc.UseExisting):
        """Create a copy of this instance replacing with specified parts."""
        attributes = zip(PARSED_COMPONENTS,
                         (scheme, userinfo, host, port, path, query, fragment))
        attrs_dict = {}
        for name, value in attributes:
            if value is misc.UseExisting:
                value = getattr(self, name)
            attrs_dict[name] = value
        authority = self._generate_authority(attrs_dict)
        ref = self.reference.copy_with(scheme=attrs_dict['scheme'],
                                       authority=authority,
                                       path=attrs_dict['path'],
                                       query=attrs_dict['query'],
                                       fragment=attrs_dict['fragment'])
        return ParseResult(uri_ref=ref, encoding=self.encoding, **attrs_dict)

    def encode(self, encoding=None):
        """Convert to an instance of ParseResultBytes."""
        encoding = encoding or self.encoding
        attrs = dict(
            zip(PARSED_COMPONENTS,
                (attr.encode(encoding) if hasattr(attr, 'encode') else attr
                 for attr in self)))
        return ParseResultBytes(
            uri_ref=self.reference,
            encoding=encoding,
            **attrs
        )

    def unsplit(self, use_idna=False):
        """Create a URI string from the components.

        :returns: The parsed URI reconstituted as a string.
        :rtype: str
        """
        parse_result = self
        if use_idna and self.host:
            hostbytes = self.host.encode('idna')
            host = hostbytes.decode(self.encoding)
            parse_result = self.copy_with(host=host)
        return parse_result.reference.unsplit()


class ParseResultBytes(namedtuple('ParseResultBytes', PARSED_COMPONENTS),
                       ParseResultMixin):
    """Compatibility shim for the urlparse.ParseResultBytes object."""

    def __new__(cls, scheme, userinfo, host, port, path, query, fragment,
                uri_ref, encoding='utf-8', lazy_normalize=True):
        """Create a new ParseResultBytes instance."""
        parse_result = super(ParseResultBytes, cls).__new__(
            cls,
            scheme or None,
            userinfo or None,
            host,
            port or None,
            path or None,
            query or None,
            fragment or None)
        parse_result.encoding = encoding
        parse_result.reference = uri_ref
        parse_result.lazy_normalize = lazy_normalize
        return parse_result

    @classmethod
    def from_parts(cls, scheme=None, userinfo=None, host=None, port=None,
                   path=None, query=None, fragment=None, encoding='utf-8',
                   lazy_normalize=True):
        """Create a ParseResult instance from its parts."""
        authority = ''
        if userinfo is not None:
            authority += userinfo + '@'
        if host is not None:
            authority += host
        if port is not None:
            authority += ':{0}'.format(int(port))
        uri_ref = uri.URIReference(scheme=scheme,
                                   authority=authority,
                                   path=path,
                                   query=query,
                                   fragment=fragment,
                                   encoding=encoding)
        if not lazy_normalize:
            uri_ref = uri_ref.normalize()
        to_bytes = compat.to_bytes
        userinfo, host, port = authority_from(uri_ref, strict=True)
        return cls(scheme=to_bytes(scheme, encoding),
                   userinfo=to_bytes(userinfo, encoding),
                   host=to_bytes(host, encoding),
                   port=port,
                   path=to_bytes(path, encoding),
                   query=to_bytes(query, encoding),
                   fragment=to_bytes(fragment, encoding),
                   uri_ref=uri_ref,
                   encoding=encoding,
                   lazy_normalize=lazy_normalize)

    @classmethod
    def from_string(cls, uri_string, encoding='utf-8', strict=True,
                    lazy_normalize=True):
        """Parse a URI from the given unicode URI string.

        :param str uri_string: Unicode URI to be parsed into a reference.
        :param str encoding: The encoding of the string provided
        :param bool strict: Parse strictly according to :rfc:`3986` if True.
            If False, parse similarly to the standard library's urlparse
            function.
        :returns: :class:`ParseResultBytes` or subclass thereof
        """
        reference = uri.URIReference.from_string(uri_string, encoding)
        if not lazy_normalize:
            reference = reference.normalize()
        userinfo, host, port = authority_from(reference, strict)

        to_bytes = compat.to_bytes
        return cls(scheme=to_bytes(reference.scheme, encoding),
                   userinfo=to_bytes(userinfo, encoding),
                   host=to_bytes(host, encoding),
                   port=port,
                   path=to_bytes(reference.path, encoding),
                   query=to_bytes(reference.query, encoding),
                   fragment=to_bytes(reference.fragment, encoding),
                   uri_ref=reference,
                   encoding=encoding,
                   lazy_normalize=lazy_normalize)

    @property
    def authority(self):
        """Return the normalized authority."""
        return self.reference.authority.encode(self.encoding)

    def copy_with(self, scheme=misc.UseExisting, userinfo=misc.UseExisting,
                  host=misc.UseExisting, port=misc.UseExisting,
                  path=misc.UseExisting, query=misc.UseExisting,
                  fragment=misc.UseExisting, lazy_normalize=True):
        """Create a copy of this instance replacing with specified parts."""
        attributes = zip(PARSED_COMPONENTS,
                         (scheme, userinfo, host, port, path, query, fragment))
        attrs_dict = {}
        for name, value in attributes:
            if value is misc.UseExisting:
                value = getattr(self, name)
            if not isinstance(value, bytes) and hasattr(value, 'encode'):
                value = value.encode(self.encoding)
            attrs_dict[name] = value
        authority = self._generate_authority(attrs_dict)
        to_str = compat.to_str
        ref = self.reference.copy_with(
            scheme=to_str(attrs_dict['scheme'], self.encoding),
            authority=to_str(authority, self.encoding),
            path=to_str(attrs_dict['path'], self.encoding),
            query=to_str(attrs_dict['query'], self.encoding),
            fragment=to_str(attrs_dict['fragment'], self.encoding)
        )
        if not lazy_normalize:
            ref = ref.normalize()
        return ParseResultBytes(
            uri_ref=ref,
            encoding=self.encoding,
            lazy_normalize=lazy_normalize,
            **attrs_dict
        )

    def unsplit(self, use_idna=False):
        """Create a URI bytes object from the components.

        :returns: The parsed URI reconstituted as a string.
        :rtype: bytes
        """
        parse_result = self
        if use_idna and self.host:
            # self.host is bytes, to encode to idna, we need to decode it
            # first
            host = self.host.decode(self.encoding)
            hostbytes = host.encode('idna')
            parse_result = self.copy_with(host=hostbytes)
        if self.lazy_normalize:
            parse_result = parse_result.copy_with(lazy_normalize=False)
        uri = parse_result.reference.unsplit()
        return uri.encode(self.encoding)


def split_authority(authority):
    # Initialize our expected return values
    userinfo = host = port = None
    # Initialize an extra var we may need to use
    extra_host = None
    # Set-up rest in case there is no userinfo portion
    rest = authority

    if '@' in authority:
        userinfo, rest = authority.rsplit('@', 1)

    # Handle IPv6 host addresses
    if rest.startswith('['):
        host, rest = rest.split(']', 1)
        host += ']'

    if ':' in rest:
        extra_host, port = rest.split(':', 1)
    elif not host and rest:
        host = rest

    if extra_host and not host:
        host = extra_host

    return userinfo, host, port


def authority_from(reference, strict):
    try:
        subauthority = reference.authority_info()
    except exceptions.InvalidAuthority:
        if strict:
            raise
        userinfo, host, port = split_authority(reference.authority)
    else:
        # Thanks to Richard Barrell for this idea:
        # https://twitter.com/0x2ba22e11/status/617338811975139328
        userinfo, host, port = (subauthority.get(p)
                                for p in ('userinfo', 'host', 'port'))

    if port:
        try:
            port = int(port)
        except ValueError:
            raise exceptions.InvalidPort(port)
    return userinfo, host, port
