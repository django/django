"""Default formatting class for Flake8."""
from __future__ import annotations

from flake8.formatting import base
from flake8.violation import Violation

COLORS = {
    "bold": "\033[1m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "reset": "\033[m",
}
COLORS_OFF = {k: "" for k in COLORS}


class SimpleFormatter(base.BaseFormatter):
    """Simple abstraction for Default and Pylint formatter commonality.

    Sub-classes of this need to define an ``error_format`` attribute in order
    to succeed. The ``format`` method relies on that attribute and expects the
    ``error_format`` string to use the old-style formatting strings with named
    parameters:

    * code
    * text
    * path
    * row
    * col

    """

    error_format: str

    def format(self, error: Violation) -> str | None:
        """Format and write error out.

        If an output filename is specified, write formatted errors to that
        file. Otherwise, print the formatted error to standard out.
        """
        return self.error_format % {
            "code": error.code,
            "text": error.text,
            "path": error.filename,
            "row": error.line_number,
            "col": error.column_number,
            **(COLORS if self.color else COLORS_OFF),
        }


class Default(SimpleFormatter):
    """Default formatter for Flake8.

    This also handles backwards compatibility for people specifying a custom
    format string.
    """

    error_format = (
        "%(bold)s%(path)s%(reset)s"
        "%(cyan)s:%(reset)s%(row)d%(cyan)s:%(reset)s%(col)d%(cyan)s:%(reset)s "
        "%(bold)s%(red)s%(code)s%(reset)s %(text)s"
    )

    def after_init(self) -> None:
        """Check for a custom format string."""
        if self.options.format.lower() != "default":
            self.error_format = self.options.format


class Pylint(SimpleFormatter):
    """Pylint formatter for Flake8."""

    error_format = "%(path)s:%(row)d: [%(code)s] %(text)s"


class FilenameOnly(SimpleFormatter):
    """Only print filenames, e.g., flake8 -q."""

    error_format = "%(path)s"

    def after_init(self) -> None:
        """Initialize our set of filenames."""
        self.filenames_already_printed: set[str] = set()

    def show_source(self, error: Violation) -> str | None:
        """Do not include the source code."""

    def format(self, error: Violation) -> str | None:
        """Ensure we only print each error once."""
        if error.filename not in self.filenames_already_printed:
            self.filenames_already_printed.add(error.filename)
            return super().format(error)
        else:
            return None


class Nothing(base.BaseFormatter):
    """Print absolutely nothing."""

    def format(self, error: Violation) -> str | None:
        """Do nothing."""

    def show_source(self, error: Violation) -> str | None:
        """Do not print the source."""
