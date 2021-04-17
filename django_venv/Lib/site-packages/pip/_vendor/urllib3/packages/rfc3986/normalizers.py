# -*- coding: utf-8 -*-
# Copyright (c) 2014 Rackspace
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
"""Module with functions to normalize components."""
import re

from . import compat
from . import misc


def normalize_scheme(scheme):
    """Normalize the scheme component."""
    return scheme.lower()


def normalize_authority(authority):
    """Normalize an authority tuple to a string."""
    userinfo, host, port = authority
    result = ''
    if userinfo:
        result += normalize_percent_characters(userinfo) + '@'
    if host:
        result += normalize_host(host)
    if port:
        result += ':' + port
    return result


def normalize_username(username):
    """Normalize a username to make it safe to include in userinfo."""
    return compat.urlquote(username)


def normalize_password(password):
    """Normalize a password to make safe for userinfo."""
    return compat.urlquote(password)


def normalize_host(host):
    """Normalize a host string."""
    if misc.IPv6_MATCHER.match(host):
        percent = host.find('%')
        if percent != -1:
            percent_25 = host.find('%25')

            # Replace RFC 4007 IPv6 Zone ID delimiter '%' with '%25'
            # from RFC 6874. If the host is '[<IPv6 addr>%25]' then we
            # assume RFC 4007 and normalize to '[<IPV6 addr>%2525]'
            if percent_25 == -1 or percent < percent_25 or \
                    (percent == percent_25 and percent_25 == len(host) - 4):
                host = host.replace('%', '%25', 1)

            # Don't normalize the casing of the Zone ID
            return host[:percent].lower() + host[percent:]

    return host.lower()


def normalize_path(path):
    """Normalize the path string."""
    if not path:
        return path

    path = normalize_percent_characters(path)
    return remove_dot_segments(path)


def normalize_query(query):
    """Normalize the query string."""
    if not query:
        return query
    return normalize_percent_characters(query)


def normalize_fragment(fragment):
    """Normalize the fragment string."""
    if not fragment:
        return fragment
    return normalize_percent_characters(fragment)


PERCENT_MATCHER = re.compile('%[A-Fa-f0-9]{2}')


def normalize_percent_characters(s):
    """All percent characters should be upper-cased.

    For example, ``"%3afoo%DF%ab"`` should be turned into ``"%3Afoo%DF%AB"``.
    """
    matches = set(PERCENT_MATCHER.findall(s))
    for m in matches:
        if not m.isupper():
            s = s.replace(m, m.upper())
    return s


def remove_dot_segments(s):
    """Remove dot segments from the string.

    See also Section 5.2.4 of :rfc:`3986`.
    """
    # See http://tools.ietf.org/html/rfc3986#section-5.2.4 for pseudo-code
    segments = s.split('/')  # Turn the path into a list of segments
    output = []  # Initialize the variable to use to store output

    for segment in segments:
        # '.' is the current directory, so ignore it, it is superfluous
        if segment == '.':
            continue
        # Anything other than '..', should be appended to the output
        elif segment != '..':
            output.append(segment)
        # In this case segment == '..', if we can, we should pop the last
        # element
        elif output:
            output.pop()

    # If the path starts with '/' and the output is empty or the first string
    # is non-empty
    if s.startswith('/') and (not output or output[0]):
        output.insert(0, '')

    # If the path starts with '/.' or '/..' ensure we add one more empty
    # string to add a trailing '/'
    if s.endswith(('/.', '/..')):
        output.append('')

    return '/'.join(output)


def encode_component(uri_component, encoding):
    """Encode the specific component in the provided encoding."""
    if uri_component is None:
        return uri_component

    # Try to see if the component we're encoding is already percent-encoded
    # so we can skip all '%' characters but still encode all others.
    percent_encodings = len(PERCENT_MATCHER.findall(
                            compat.to_str(uri_component, encoding)))

    uri_bytes = compat.to_bytes(uri_component, encoding)
    is_percent_encoded = percent_encodings == uri_bytes.count(b'%')

    encoded_uri = bytearray()

    for i in range(0, len(uri_bytes)):
        # Will return a single character bytestring on both Python 2 & 3
        byte = uri_bytes[i:i+1]
        byte_ord = ord(byte)
        if ((is_percent_encoded and byte == b'%')
                or (byte_ord < 128 and byte.decode() in misc.NON_PCT_ENCODED)):
            encoded_uri.extend(byte)
            continue
        encoded_uri.extend('%{0:02x}'.format(byte_ord).encode().upper())

    return encoded_uri.decode(encoding)
