"""Contains SphinxError and a few subclasses."""

from __future__ import annotations

from typing import Any


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

    def __init__(
        self, message: str, orig_exc: Exception | None = None, modname: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.orig_exc = orig_exc
        self.modname = modname

    @property
    def category(self) -> str:  # type: ignore[override]
        if self.modname:
            return 'Extension error (%s)' % self.modname
        else:
            return 'Extension error'

    def __repr__(self) -> str:
        if self.orig_exc:
            return f'{self.__class__.__name__}({self.message!r}, {self.orig_exc!r})'
        return f'{self.__class__.__name__}({self.message!r})'

    def __str__(self) -> str:
        parent_str = super().__str__()
        if self.orig_exc:
            return f'{parent_str} (exception: {self.orig_exc})'
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

    def __init__(self, message: str, traceback: Any) -> None:
        self.message = message
        self.traceback = traceback

    def __str__(self) -> str:
        return self.message


class PycodeError(Exception):
    """Pycode Python source code analyser error."""

    def __str__(self) -> str:
        res = self.args[0]
        if len(self.args) > 1:
            res += ' (exception was: %r)' % self.args[1]
        return res


class NoUri(Exception):
    """Raised by builder.get_relative_uri() or from missing-reference handlers
    if there is no URI available."""
    pass


class FiletypeNotFoundError(Exception):
    """Raised by get_filetype() if a filename matches no source suffix."""
    pass
