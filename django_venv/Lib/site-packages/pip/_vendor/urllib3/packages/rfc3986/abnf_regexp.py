# -*- coding: utf-8 -*-
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
"""Module for the regular expressions crafted from ABNF."""

import sys

# https://tools.ietf.org/html/rfc3986#page-13
GEN_DELIMS = GENERIC_DELIMITERS = ":/?#[]@"
GENERIC_DELIMITERS_SET = set(GENERIC_DELIMITERS)
# https://tools.ietf.org/html/rfc3986#page-13
SUB_DELIMS = SUB_DELIMITERS = "!$&'()*+,;="
SUB_DELIMITERS_SET = set(SUB_DELIMITERS)
# Escape the '*' for use in regular expressions
SUB_DELIMITERS_RE = r"!$&'()\*+,;="
RESERVED_CHARS_SET = GENERIC_DELIMITERS_SET.union(SUB_DELIMITERS_SET)
ALPHA = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
DIGIT = '0123456789'
# https://tools.ietf.org/html/rfc3986#section-2.3
UNRESERVED = UNRESERVED_CHARS = ALPHA + DIGIT + r'._!-'
UNRESERVED_CHARS_SET = set(UNRESERVED_CHARS)
NON_PCT_ENCODED_SET = RESERVED_CHARS_SET.union(UNRESERVED_CHARS_SET)
# We need to escape the '-' in this case:
UNRESERVED_RE = r'A-Za-z0-9._~\-'

# Percent encoded character values
PERCENT_ENCODED = PCT_ENCODED = '%[A-Fa-f0-9]{2}'
PCHAR = '([' + UNRESERVED_RE + SUB_DELIMITERS_RE + ':@]|%s)' % PCT_ENCODED

# NOTE(sigmavirus24): We're going to use more strict regular expressions
# than appear in Appendix B for scheme. This will prevent over-eager
# consuming of items that aren't schemes.
SCHEME_RE = '[a-zA-Z][a-zA-Z0-9+.-]*'
_AUTHORITY_RE = '[^/?#]*'
_PATH_RE = '[^?#]*'
_QUERY_RE = '[^#]*'
_FRAGMENT_RE = '.*'

# Extracted from http://tools.ietf.org/html/rfc3986#appendix-B
COMPONENT_PATTERN_DICT = {
    'scheme': SCHEME_RE,
    'authority': _AUTHORITY_RE,
    'path': _PATH_RE,
    'query': _QUERY_RE,
    'fragment': _FRAGMENT_RE,
}

# See http://tools.ietf.org/html/rfc3986#appendix-B
# In this case, we name each of the important matches so we can use
# SRE_Match#groupdict to parse the values out if we so choose. This is also
# modified to ignore other matches that are not important to the parsing of
# the reference so we can also simply use SRE_Match#groups.
URL_PARSING_RE = (
    r'(?:(?P<scheme>{scheme}):)?(?://(?P<authority>{authority}))?'
    r'(?P<path>{path})(?:\?(?P<query>{query}))?'
    r'(?:#(?P<fragment>{fragment}))?'
).format(**COMPONENT_PATTERN_DICT)


# #########################
# Authority Matcher Section
# #########################

# Host patterns, see: http://tools.ietf.org/html/rfc3986#section-3.2.2
# The pattern for a regular name, e.g.,  www.google.com, api.github.com
REGULAR_NAME_RE = REG_NAME = '((?:{0}|[{1}])*)'.format(
    '%[0-9A-Fa-f]{2}', SUB_DELIMITERS_RE + UNRESERVED_RE
)
# The pattern for an IPv4 address, e.g., 192.168.255.255, 127.0.0.1,
IPv4_RE = r'([0-9]{1,3}\.){3}[0-9]{1,3}'
# Hexadecimal characters used in each piece of an IPv6 address
HEXDIG_RE = '[0-9A-Fa-f]{1,4}'
# Least-significant 32 bits of an IPv6 address
LS32_RE = '({hex}:{hex}|{ipv4})'.format(hex=HEXDIG_RE, ipv4=IPv4_RE)
# Substitutions into the following patterns for IPv6 patterns defined
# http://tools.ietf.org/html/rfc3986#page-20
_subs = {'hex': HEXDIG_RE, 'ls32': LS32_RE}

# Below: h16 = hexdig, see: https://tools.ietf.org/html/rfc5234 for details
# about ABNF (Augmented Backus-Naur Form) use in the comments
variations = [
    #                            6( h16 ":" ) ls32
    '(%(hex)s:){6}%(ls32)s' % _subs,
    #                       "::" 5( h16 ":" ) ls32
    '::(%(hex)s:){5}%(ls32)s' % _subs,
    # [               h16 ] "::" 4( h16 ":" ) ls32
    '(%(hex)s)?::(%(hex)s:){4}%(ls32)s' % _subs,
    # [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
    '((%(hex)s:)?%(hex)s)?::(%(hex)s:){3}%(ls32)s' % _subs,
    # [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
    '((%(hex)s:){0,2}%(hex)s)?::(%(hex)s:){2}%(ls32)s' % _subs,
    # [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
    '((%(hex)s:){0,3}%(hex)s)?::%(hex)s:%(ls32)s' % _subs,
    # [ *4( h16 ":" ) h16 ] "::"              ls32
    '((%(hex)s:){0,4}%(hex)s)?::%(ls32)s' % _subs,
    # [ *5( h16 ":" ) h16 ] "::"              h16
    '((%(hex)s:){0,5}%(hex)s)?::%(hex)s' % _subs,
    # [ *6( h16 ":" ) h16 ] "::"
    '((%(hex)s:){0,6}%(hex)s)?::' % _subs,
]

IPv6_RE = '(({0})|({1})|({2})|({3})|({4})|({5})|({6})|({7})|({8}))'.format(
    *variations
)

IPv_FUTURE_RE = r'v[0-9A-Fa-f]+\.[%s]+' % (
    UNRESERVED_RE + SUB_DELIMITERS_RE + ':'
)

# RFC 6874 Zone ID ABNF
ZONE_ID = '(?:[' + UNRESERVED_RE + ']|' + PCT_ENCODED + ')+'

IPv6_ADDRZ_RFC4007_RE = IPv6_RE + '(?:(?:%25|%)' + ZONE_ID + ')?'
IPv6_ADDRZ_RE = IPv6_RE + '(?:%25' + ZONE_ID + ')?'

IP_LITERAL_RE = r'\[({0}|{1})\]'.format(
    IPv6_ADDRZ_RFC4007_RE,
    IPv_FUTURE_RE,
)

# Pattern for matching the host piece of the authority
HOST_RE = HOST_PATTERN = '({0}|{1}|{2})'.format(
    REG_NAME,
    IPv4_RE,
    IP_LITERAL_RE,
)
USERINFO_RE = '^([' + UNRESERVED_RE + SUB_DELIMITERS_RE + ':]|%s)+' % (
    PCT_ENCODED
)
PORT_RE = '[0-9]{1,5}'

# ####################
# Path Matcher Section
# ####################

# See http://tools.ietf.org/html/rfc3986#section-3.3 for more information
# about the path patterns defined below.
segments = {
    'segment': PCHAR + '*',
    # Non-zero length segment
    'segment-nz': PCHAR + '+',
    # Non-zero length segment without ":"
    'segment-nz-nc': PCHAR.replace(':', '') + '+'
}

# Path types taken from Section 3.3 (linked above)
PATH_EMPTY = '^$'
PATH_ROOTLESS = '%(segment-nz)s(/%(segment)s)*' % segments
PATH_NOSCHEME = '%(segment-nz-nc)s(/%(segment)s)*' % segments
PATH_ABSOLUTE = '/(%s)?' % PATH_ROOTLESS
PATH_ABEMPTY = '(/%(segment)s)*' % segments
PATH_RE = '^(%s|%s|%s|%s|%s)$' % (
    PATH_ABEMPTY, PATH_ABSOLUTE, PATH_NOSCHEME, PATH_ROOTLESS, PATH_EMPTY
)

FRAGMENT_RE = QUERY_RE = (
    '^([/?:@' + UNRESERVED_RE + SUB_DELIMITERS_RE + ']|%s)*$' % PCT_ENCODED
)

# ##########################
# Relative reference matcher
# ##########################

# See http://tools.ietf.org/html/rfc3986#section-4.2 for details
RELATIVE_PART_RE = '(//%s%s|%s|%s|%s)' % (
    COMPONENT_PATTERN_DICT['authority'],
    PATH_ABEMPTY,
    PATH_ABSOLUTE,
    PATH_NOSCHEME,
    PATH_EMPTY,
)

# See http://tools.ietf.org/html/rfc3986#section-3 for definition
HIER_PART_RE = '(//%s%s|%s|%s|%s)' % (
    COMPONENT_PATTERN_DICT['authority'],
    PATH_ABEMPTY,
    PATH_ABSOLUTE,
    PATH_ROOTLESS,
    PATH_EMPTY,
)

# ###############
# IRIs / RFC 3987
# ###############

# Only wide-unicode gets the high-ranges of UCSCHAR
if sys.maxunicode > 0xFFFF:  # pragma: no cover
    IPRIVATE = u'\uE000-\uF8FF\U000F0000-\U000FFFFD\U00100000-\U0010FFFD'
    UCSCHAR_RE = (
        u'\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF'
        u'\U00010000-\U0001FFFD\U00020000-\U0002FFFD'
        u'\U00030000-\U0003FFFD\U00040000-\U0004FFFD'
        u'\U00050000-\U0005FFFD\U00060000-\U0006FFFD'
        u'\U00070000-\U0007FFFD\U00080000-\U0008FFFD'
        u'\U00090000-\U0009FFFD\U000A0000-\U000AFFFD'
        u'\U000B0000-\U000BFFFD\U000C0000-\U000CFFFD'
        u'\U000D0000-\U000DFFFD\U000E1000-\U000EFFFD'
    )
else:  # pragma: no cover
    IPRIVATE = u'\uE000-\uF8FF'
    UCSCHAR_RE = (
        u'\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF'
    )

IUNRESERVED_RE = u'A-Za-z0-9\\._~\\-' + UCSCHAR_RE
IPCHAR = u'([' + IUNRESERVED_RE + SUB_DELIMITERS_RE + u':@]|%s)' % PCT_ENCODED

isegments = {
    'isegment': IPCHAR + u'*',
    # Non-zero length segment
    'isegment-nz': IPCHAR + u'+',
    # Non-zero length segment without ":"
    'isegment-nz-nc': IPCHAR.replace(':', '') + u'+'
}

IPATH_ROOTLESS = u'%(isegment-nz)s(/%(isegment)s)*' % isegments
IPATH_NOSCHEME = u'%(isegment-nz-nc)s(/%(isegment)s)*' % isegments
IPATH_ABSOLUTE = u'/(?:%s)?' % IPATH_ROOTLESS
IPATH_ABEMPTY = u'(?:/%(isegment)s)*' % isegments
IPATH_RE = u'^(?:%s|%s|%s|%s|%s)$' % (
    IPATH_ABEMPTY, IPATH_ABSOLUTE, IPATH_NOSCHEME, IPATH_ROOTLESS, PATH_EMPTY
)

IREGULAR_NAME_RE = IREG_NAME = u'(?:{0}|[{1}])*'.format(
    u'%[0-9A-Fa-f]{2}', SUB_DELIMITERS_RE + IUNRESERVED_RE
)

IHOST_RE = IHOST_PATTERN = u'({0}|{1}|{2})'.format(
    IREG_NAME,
    IPv4_RE,
    IP_LITERAL_RE,
)

IUSERINFO_RE = u'^(?:[' + IUNRESERVED_RE + SUB_DELIMITERS_RE + u':]|%s)+' % (
    PCT_ENCODED
)

IFRAGMENT_RE = (u'^(?:[/?:@' + IUNRESERVED_RE + SUB_DELIMITERS_RE
                + u']|%s)*$' % PCT_ENCODED)
IQUERY_RE = (u'^(?:[/?:@' + IUNRESERVED_RE + SUB_DELIMITERS_RE
             + IPRIVATE + u']|%s)*$' % PCT_ENCODED)

IRELATIVE_PART_RE = u'(//%s%s|%s|%s|%s)' % (
    COMPONENT_PATTERN_DICT['authority'],
    IPATH_ABEMPTY,
    IPATH_ABSOLUTE,
    IPATH_NOSCHEME,
    PATH_EMPTY,
)

IHIER_PART_RE = u'(//%s%s|%s|%s|%s)' % (
    COMPONENT_PATTERN_DICT['authority'],
    IPATH_ABEMPTY,
    IPATH_ABSOLUTE,
    IPATH_ROOTLESS,
    PATH_EMPTY,
)
