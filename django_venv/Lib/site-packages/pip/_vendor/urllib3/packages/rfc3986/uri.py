"""Module containing the implementation of the URIReference class."""
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Rackspace
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
from collections import namedtuple

from . import compat
from . import misc
from . import normalizers
from ._mixin import URIMixin


class URIReference(namedtuple('URIReference', misc.URI_COMPONENTS), URIMixin):
    """Immutable object representing a parsed URI Reference.

    .. note::

        This class is not intended to be directly instantiated by the user.

    This object exposes attributes for the following components of a
    URI:

    - scheme
    - authority
    - path
    - query
    - fragment

    .. attribute:: scheme

        The scheme that was parsed for the URI Reference. For example,
        ``http``, ``https``, ``smtp``, ``imap``, etc.

    .. attribute:: authority

        Component of the URI that contains the user information, host,
        and port sub-components. For example,
        ``google.com``, ``127.0.0.1:5000``, ``username@[::1]``,
        ``username:password@example.com:443``, etc.

    .. attribute:: path

        The path that was parsed for the given URI Reference. For example,
        ``/``, ``/index.php``, etc.

    .. attribute:: query

        The query component for a given URI Reference. For example, ``a=b``,
        ``a=b%20c``, ``a=b+c``, ``a=b,c=d,e=%20f``, etc.

    .. attribute:: fragment

        The fragment component of a URI. For example, ``section-3.1``.

    This class also provides extra attributes for easier access to information
    like the subcomponents of the authority component.

    .. attribute:: userinfo

        The user information parsed from the authority.

    .. attribute:: host

        The hostname, IPv4, or IPv6 adddres parsed from the authority.

    .. attribute:: port

        The port parsed from the authority.
    """

    slots = ()

    def __new__(cls, scheme, authority, path, query, fragment,
                encoding='utf-8'):
        """Create a new URIReference."""
        ref = super(URIReference, cls).__new__(
            cls,
            scheme or None,
            authority or None,
            path or None,
            query,
            fragment)
        ref.encoding = encoding
        return ref

    __hash__ = tuple.__hash__

    def __eq__(self, other):
        """Compare this reference to another."""
        other_ref = other
        if isinstance(other, tuple):
            other_ref = URIReference(*other)
        elif not isinstance(other, URIReference):
            try:
                other_ref = URIReference.from_string(other)
            except TypeError:
                raise TypeError(
                    'Unable to compare URIReference() to {0}()'.format(
                        type(other).__name__))

        # See http://tools.ietf.org/html/rfc3986#section-6.2
        naive_equality = tuple(self) == tuple(other_ref)
        return naive_equality or self.normalized_equality(other_ref)

    def normalize(self):
        """Normalize this reference as described in Section 6.2.2.

        This is not an in-place normalization. Instead this creates a new
        URIReference.

        :returns: A new reference object with normalized components.
        :rtype: URIReference
        """
        # See http://tools.ietf.org/html/rfc3986#section-6.2.2 for logic in
        # this method.
        return URIReference(normalizers.normalize_scheme(self.scheme or ''),
                            normalizers.normalize_authority(
                                (self.userinfo, self.host, self.port)),
                            normalizers.normalize_path(self.path or ''),
                            normalizers.normalize_query(self.query),
                            normalizers.normalize_fragment(self.fragment),
                            self.encoding)

    @classmethod
    def from_string(cls, uri_string, encoding='utf-8'):
        """Parse a URI reference from the given unicode URI string.

        :param str uri_string: Unicode URI to be parsed into a reference.
        :param str encoding: The encoding of the string provided
        :returns: :class:`URIReference` or subclass thereof
        """
        uri_string = compat.to_str(uri_string, encoding)

        split_uri = misc.URI_MATCHER.match(uri_string).groupdict()
        return cls(
            split_uri['scheme'], split_uri['authority'],
            normalizers.encode_component(split_uri['path'], encoding),
            normalizers.encode_component(split_uri['query'], encoding),
            normalizers.encode_component(split_uri['fragment'], encoding),
            encoding,
        )
