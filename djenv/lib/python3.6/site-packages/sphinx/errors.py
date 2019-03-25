# -*- coding: utf-8 -*-
"""
    sphinx.errors
    ~~~~~~~~~~~~~

    Contains SphinxError and a few subclasses (in an extra module to avoid
    circular import problems).

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

if False:
    # For type annotation
    from typing import Any  # NOQA


class SphinxError(Exception):
    """Base class for Sphinx errors.

    This is the base class for "nice" exceptions.  When such an exception is
    raised, Sphinx will abort the build and present the exception category and
    message to the user.

    Extensions are encouraged to derive from this exception for their custom
    errors.

    Exceptions *not* derived from :exc:`SphinxError` are treated as unexpected
    and shown to the user with a part of the traceback (and the full traceback
    saved in a temporary file).

    .. attribute:: category

       Description of the exception "category", used in converting the
       exception to a string ("category: message").  Should be set accordingly
       in subclasses.
    """
    category = 'Sphinx error'


class SphinxWarning(SphinxError):
    """Warning, treated as error."""
    category = 'Warning, treated as error'


class ApplicationError(SphinxError):
    """Application initialization error."""
    category = 'Application error'


class ExtensionError(SphinxError):
    """Extension error."""
    category = 'Extension error'

    def __init__(self, message, orig_exc=None):
        # type: (unicode, Exception) -> None
        SphinxError.__init__(self, message)
        self.message = message
        self.orig_exc = orig_exc

    def __repr__(self):
        # type: () -> str
        if self.orig_exc:
            return '%s(%r, %r)' % (self.__class__.__name__,
                                   self.message, self.orig_exc)
        return '%s(%r)' % (self.__class__.__name__, self.message)

    def __str__(self):
        # type: () -> str
        parent_str = SphinxError.__str__(self)
        if self.orig_exc:
            return '%s (exception: %s)' % (parent_str, self.orig_exc)
        return parent_str


class BuildEnvironmentError(SphinxError):
    """BuildEnvironment error."""
    category = 'BuildEnvironment error'


class ConfigError(SphinxError):
    """Configuration error."""
    category = 'Configuration error'


class DocumentError(SphinxError):
    """Document error."""
    category = 'Document error'


class ThemeError(SphinxError):
    """Theme error."""
    category = 'Theme error'


class VersionRequirementError(SphinxError):
    """Incompatible Sphinx version error."""
    category = 'Sphinx version error'


class SphinxParallelError(SphinxError):
    """Sphinx parallel build error."""

    category = 'Sphinx parallel build error'

    def __init__(self, message, traceback):
        # type: (str, Any) -> None
        self.message = message
        self.traceback = traceback

    def __str__(self):
        # type: () -> str
        return self.message


class PycodeError(Exception):
    """Pycode Python source code analyser error."""

    def __str__(self):
        # type: () -> str
        res = self.args[0]
        if len(self.args) > 1:
            res += ' (exception was: %r)' % self.args[1]
        return res
