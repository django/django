# -*- coding: utf-8 -*-
# Copyright (c) 2017 Ian Stapleton Cordasco
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
"""Module containing the validation logic for rfc3986."""
from . import exceptions
from . import misc
from . import normalizers


class Validator(object):
    """Object used to configure validation of all objects in rfc3986.

    .. versionadded:: 1.0

    Example usage::

         >>> from rfc3986 import api, validators
         >>> uri = api.uri_reference('https://github.com/')
         >>> validator = validators.Validator().require_presence_of(
         ...    'scheme', 'host', 'path',
         ... ).allow_schemes(
         ...    'http', 'https',
         ... ).allow_hosts(
         ...    '127.0.0.1', 'github.com',
         ... )
         >>> validator.validate(uri)
         >>> invalid_uri = rfc3986.uri_reference('imap://mail.google.com')
         >>> validator.validate(invalid_uri)
         Traceback (most recent call last):
         ...
         rfc3986.exceptions.MissingComponentError: ('path was required but
         missing', URIReference(scheme=u'imap', authority=u'mail.google.com',
         path=None, query=None, fragment=None), ['path'])

    """

    COMPONENT_NAMES = frozenset([
        'scheme',
        'userinfo',
        'host',
        'port',
        'path',
        'query',
        'fragment',
    ])

    def __init__(self):
        """Initialize our default validations."""
        self.allowed_schemes = set()
        self.allowed_hosts = set()
        self.allowed_ports = set()
        self.allow_password = True
        self.required_components = {
            'scheme': False,
            'userinfo': False,
            'host': False,
            'port': False,
            'path': False,
            'query': False,
            'fragment': False,
        }
        self.validated_components = self.required_components.copy()

    def allow_schemes(self, *schemes):
        """Require the scheme to be one of the provided schemes.

        .. versionadded:: 1.0

        :param schemes:
            Schemes, without ``://`` that are allowed.
        :returns:
            The validator instance.
        :rtype:
            Validator
        """
        for scheme in schemes:
            self.allowed_schemes.add(normalizers.normalize_scheme(scheme))
        return self

    def allow_hosts(self, *hosts):
        """Require the host to be one of the provided hosts.

        .. versionadded:: 1.0

        :param hosts:
            Hosts that are allowed.
        :returns:
            The validator instance.
        :rtype:
            Validator
        """
        for host in hosts:
            self.allowed_hosts.add(normalizers.normalize_host(host))
        return self

    def allow_ports(self, *ports):
        """Require the port to be one of the provided ports.

        .. versionadded:: 1.0

        :param ports:
            Ports that are allowed.
        :returns:
            The validator instance.
        :rtype:
            Validator
        """
        for port in ports:
            port_int = int(port, base=10)
            if 0 <= port_int <= 65535:
                self.allowed_ports.add(port)
        return self

    def allow_use_of_password(self):
        """Allow passwords to be present in the URI.

        .. versionadded:: 1.0

        :returns:
            The validator instance.
        :rtype:
            Validator
        """
        self.allow_password = True
        return self

    def forbid_use_of_password(self):
        """Prevent passwords from being included in the URI.

        .. versionadded:: 1.0

        :returns:
            The validator instance.
        :rtype:
            Validator
        """
        self.allow_password = False
        return self

    def check_validity_of(self, *components):
        """Check the validity of the components provided.

        This can be specified repeatedly.

        .. versionadded:: 1.1

        :param components:
            Names of components from :attr:`Validator.COMPONENT_NAMES`.
        :returns:
            The validator instance.
        :rtype:
            Validator
        """
        components = [c.lower() for c in components]
        for component in components:
            if component not in self.COMPONENT_NAMES:
                raise ValueError(
                    '"{}" is not a valid component'.format(component)
                )
        self.validated_components.update({
            component: True for component in components
        })
        return self

    def require_presence_of(self, *components):
        """Require the components provided.

        This can be specified repeatedly.

        .. versionadded:: 1.0

        :param components:
            Names of components from :attr:`Validator.COMPONENT_NAMES`.
        :returns:
            The validator instance.
        :rtype:
            Validator
        """
        components = [c.lower() for c in components]
        for component in components:
            if component not in self.COMPONENT_NAMES:
                raise ValueError(
                    '"{}" is not a valid component'.format(component)
                )
        self.required_components.update({
            component: True for component in components
        })
        return self

    def validate(self, uri):
        """Check a URI for conditions specified on this validator.

        .. versionadded:: 1.0

        :param uri:
            Parsed URI to validate.
        :type uri:
            rfc3986.uri.URIReference
        :raises MissingComponentError:
            When a required component is missing.
        :raises UnpermittedComponentError:
            When a component is not one of those allowed.
        :raises PasswordForbidden:
            When a password is present in the userinfo component but is
            not permitted by configuration.
        :raises InvalidComponentsError:
            When a component was found to be invalid.
        """
        if not self.allow_password:
            check_password(uri)

        required_components = [
            component
            for component, required in self.required_components.items()
            if required
        ]
        validated_components = [
            component
            for component, required in self.validated_components.items()
            if required
        ]
        if required_components:
            ensure_required_components_exist(uri, required_components)
        if validated_components:
            ensure_components_are_valid(uri, validated_components)

        ensure_one_of(self.allowed_schemes, uri, 'scheme')
        ensure_one_of(self.allowed_hosts, uri, 'host')
        ensure_one_of(self.allowed_ports, uri, 'port')


def check_password(uri):
    """Assert that there is no password present in the uri."""
    userinfo = uri.userinfo
    if not userinfo:
        return
    credentials = userinfo.split(':', 1)
    if len(credentials) <= 1:
        return
    raise exceptions.PasswordForbidden(uri)


def ensure_one_of(allowed_values, uri, attribute):
    """Assert that the uri's attribute is one of the allowed values."""
    value = getattr(uri, attribute)
    if value is not None and allowed_values and value not in allowed_values:
        raise exceptions.UnpermittedComponentError(
            attribute, value, allowed_values,
        )


def ensure_required_components_exist(uri, required_components):
    """Assert that all required components are present in the URI."""
    missing_components = sorted([
        component
        for component in required_components
        if getattr(uri, component) is None
    ])
    if missing_components:
        raise exceptions.MissingComponentError(uri, *missing_components)


def is_valid(value, matcher, require):
    """Determine if a value is valid based on the provided matcher.

    :param str value:
        Value to validate.
    :param matcher:
        Compiled regular expression to use to validate the value.
    :param require:
        Whether or not the value is required.
    """
    if require:
        return (value is not None
                and matcher.match(value))

    # require is False and value is not None
    return value is None or matcher.match(value)


def authority_is_valid(authority, host=None, require=False):
    """Determine if the authority string is valid.

    :param str authority:
        The authority to validate.
    :param str host:
        (optional) The host portion of the authority to validate.
    :param bool require:
        (optional) Specify if authority must not be None.
    :returns:
        ``True`` if valid, ``False`` otherwise
    :rtype:
        bool
    """
    validated = is_valid(authority, misc.SUBAUTHORITY_MATCHER, require)
    if validated and host is not None:
        return host_is_valid(host, require)
    return validated


def host_is_valid(host, require=False):
    """Determine if the host string is valid.

    :param str host:
        The host to validate.
    :param bool require:
        (optional) Specify if host must not be None.
    :returns:
        ``True`` if valid, ``False`` otherwise
    :rtype:
        bool
    """
    validated = is_valid(host, misc.HOST_MATCHER, require)
    if validated and host is not None and misc.IPv4_MATCHER.match(host):
        return valid_ipv4_host_address(host)
    elif validated and host is not None and misc.IPv6_MATCHER.match(host):
        return misc.IPv6_NO_RFC4007_MATCHER.match(host) is not None
    return validated


def scheme_is_valid(scheme, require=False):
    """Determine if the scheme is valid.

    :param str scheme:
        The scheme string to validate.
    :param bool require:
        (optional) Set to ``True`` to require the presence of a scheme.
    :returns:
        ``True`` if the scheme is valid. ``False`` otherwise.
    :rtype:
        bool
    """
    return is_valid(scheme, misc.SCHEME_MATCHER, require)


def path_is_valid(path, require=False):
    """Determine if the path component is valid.

    :param str path:
        The path string to validate.
    :param bool require:
        (optional) Set to ``True`` to require the presence of a path.
    :returns:
        ``True`` if the path is valid. ``False`` otherwise.
    :rtype:
        bool
    """
    return is_valid(path, misc.PATH_MATCHER, require)


def query_is_valid(query, require=False):
    """Determine if the query component is valid.

    :param str query:
        The query string to validate.
    :param bool require:
        (optional) Set to ``True`` to require the presence of a query.
    :returns:
        ``True`` if the query is valid. ``False`` otherwise.
    :rtype:
        bool
    """
    return is_valid(query, misc.QUERY_MATCHER, require)


def fragment_is_valid(fragment, require=False):
    """Determine if the fragment component is valid.

    :param str fragment:
        The fragment string to validate.
    :param bool require:
        (optional) Set to ``True`` to require the presence of a fragment.
    :returns:
        ``True`` if the fragment is valid. ``False`` otherwise.
    :rtype:
        bool
    """
    return is_valid(fragment, misc.FRAGMENT_MATCHER, require)


def valid_ipv4_host_address(host):
    """Determine if the given host is a valid IPv4 address."""
    # If the host exists, and it might be IPv4, check each byte in the
    # address.
    return all([0 <= int(byte, base=10) <= 255 for byte in host.split('.')])


_COMPONENT_VALIDATORS = {
    'scheme': scheme_is_valid,
    'path': path_is_valid,
    'query': query_is_valid,
    'fragment': fragment_is_valid,
}

_SUBAUTHORITY_VALIDATORS = set(['userinfo', 'host', 'port'])


def subauthority_component_is_valid(uri, component):
    """Determine if the userinfo, host, and port are valid."""
    try:
        subauthority_dict = uri.authority_info()
    except exceptions.InvalidAuthority:
        return False

    # If we can parse the authority into sub-components and we're not
    # validating the port, we can assume it's valid.
    if component == 'host':
        return host_is_valid(subauthority_dict['host'])
    elif component != 'port':
        return True

    try:
        port = int(subauthority_dict['port'])
    except TypeError:
        # If the port wasn't provided it'll be None and int(None) raises a
        # TypeError
        return True

    return (0 <= port <= 65535)


def ensure_components_are_valid(uri, validated_components):
    """Assert that all components are valid in the URI."""
    invalid_components = set([])
    for component in validated_components:
        if component in _SUBAUTHORITY_VALIDATORS:
            if not subauthority_component_is_valid(uri, component):
                invalid_components.add(component)
            # Python's peephole optimizer means that while this continue *is*
            # actually executed, coverage.py cannot detect that. See also,
            # https://bitbucket.org/ned/coveragepy/issues/198/continue-marked-as-not-covered
            continue  # nocov: Python 2.7, 3.3, 3.4

        validator = _COMPONENT_VALIDATORS[component]
        if not validator(getattr(uri, component)):
            invalid_components.add(component)

    if invalid_components:
        raise exceptions.InvalidComponentsError(uri, *invalid_components)
