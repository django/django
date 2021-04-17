# -*- coding: utf-8 -*-
"""Exceptions module for rfc3986."""

from . import compat


class RFC3986Exception(Exception):
    """Base class for all rfc3986 exception classes."""

    pass


class InvalidAuthority(RFC3986Exception):
    """Exception when the authority string is invalid."""

    def __init__(self, authority):
        """Initialize the exception with the invalid authority."""
        super(InvalidAuthority, self).__init__(
            u"The authority ({0}) is not valid.".format(
                compat.to_str(authority)))


class InvalidPort(RFC3986Exception):
    """Exception when the port is invalid."""

    def __init__(self, port):
        """Initialize the exception with the invalid port."""
        super(InvalidPort, self).__init__(
            'The port ("{0}") is not valid.'.format(port))


class ResolutionError(RFC3986Exception):
    """Exception to indicate a failure to resolve a URI."""

    def __init__(self, uri):
        """Initialize the error with the failed URI."""
        super(ResolutionError, self).__init__(
            "{0} is not an absolute URI.".format(uri.unsplit()))


class ValidationError(RFC3986Exception):
    """Exception raised during Validation of a URI."""

    pass


class MissingComponentError(ValidationError):
    """Exception raised when a required component is missing."""

    def __init__(self, uri, *component_names):
        """Initialize the error with the missing component name."""
        verb = 'was'
        if len(component_names) > 1:
            verb = 'were'

        self.uri = uri
        self.components = sorted(component_names)
        components = ', '.join(self.components)
        super(MissingComponentError, self).__init__(
            "{} {} required but missing".format(components, verb),
            uri,
            self.components,
        )


class UnpermittedComponentError(ValidationError):
    """Exception raised when a component has an unpermitted value."""

    def __init__(self, component_name, component_value, allowed_values):
        """Initialize the error with the unpermitted component."""
        super(UnpermittedComponentError, self).__init__(
            "{} was required to be one of {!r} but was {!r}".format(
                component_name, list(sorted(allowed_values)), component_value,
            ),
            component_name,
            component_value,
            allowed_values,
        )
        self.component_name = component_name
        self.component_value = component_value
        self.allowed_values = allowed_values


class PasswordForbidden(ValidationError):
    """Exception raised when a URL has a password in the userinfo section."""

    def __init__(self, uri):
        """Initialize the error with the URI that failed validation."""
        unsplit = getattr(uri, 'unsplit', lambda: uri)
        super(PasswordForbidden, self).__init__(
            '"{}" contained a password when validation forbade it'.format(
                unsplit()
            )
        )
        self.uri = uri


class InvalidComponentsError(ValidationError):
    """Exception raised when one or more components are invalid."""

    def __init__(self, uri, *component_names):
        """Initialize the error with the invalid component name(s)."""
        verb = 'was'
        if len(component_names) > 1:
            verb = 'were'

        self.uri = uri
        self.components = sorted(component_names)
        components = ', '.join(self.components)
        super(InvalidComponentsError, self).__init__(
            "{} {} found to be invalid".format(components, verb),
            uri,
            self.components,
        )


class MissingDependencyError(RFC3986Exception):
    """Exception raised when an IRI is encoded without the 'idna' module."""
