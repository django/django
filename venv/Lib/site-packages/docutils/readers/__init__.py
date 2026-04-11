# $Id: __init__.py 10077 2025-04-09 08:55:54Z milde $
# Authors: David Goodger <goodger@python.org>; Ueli Schlaepfer
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils Reader modules.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import importlib
import warnings

from docutils import utils, parsers, Component
from docutils.transforms import universal

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Final

    from docutils import nodes
    from docutils.io import Input
    from docutils.parsers import Parser
    from docutils.transforms import Transform


class Reader(Component):

    """
    Abstract base class for docutils Readers.

    Each reader module or package must export a subclass also called 'Reader'.

    The two steps of a Reader's responsibility are to read data from the
    source Input object and parse the data with the Parser object.
    Call `read()` to process a document.
    """

    component_type: Final = 'reader'
    config_section: Final = 'readers'

    def get_transforms(self) -> list[type[Transform]]:
        return super().get_transforms() + [universal.Decorations,
                                           universal.ExposeInternals,
                                           universal.StripComments]

    def __init__(self,
                 parser: Parser | str | None = None,
                 parser_name: str | None = None
                 ) -> None:
        """
        Initialize the Reader instance.

        :parser: A parser instance or name (an instance will be created).
        :parser_name: deprecated, use "parser".

        Several instance attributes are defined with dummy initial values.
        Subclasses may use these attributes as they wish.
        """

        self.parser: Parser | None = parser
        """A `parsers.Parser` instance shared by all doctrees.  May be left
        unspecified if the document source determines the parser."""

        if isinstance(parser, str):
            self.set_parser(parser)
        if parser_name is not None:
            warnings.warn('Argument "parser_name" will be removed '
                          'in Docutils 2.0.\n'
                          '  Specify parser name in the "parser" argument.',
                          PendingDeprecationWarning, stacklevel=2)
            if self.parser is None:
                self.set_parser(parser_name)

        self.source: Input | None = None
        """`docutils.io` IO object, source of input data."""

        self.input: str | None = None
        """Raw text input; either a single string or, for more complex cases,
        a collection of strings."""

    def set_parser(self, parser_name: str) -> None:
        """Set `self.parser` by name."""
        parser_class = parsers.get_parser_class(parser_name)
        self.parser = parser_class()

    def read(self, source, parser, settings):
        self.source = source
        if not self.parser:
            self.parser = parser
        self.settings = settings
        self.input = self.source.read()
        self.parse()
        return self.document

    def parse(self) -> None:
        """Parse `self.input` into a document tree."""
        document = self.new_document()
        self.parser.parse(self.input, document)
        document.current_source = document.current_line = None
        self.document: nodes.document = document

    def new_document(self) -> nodes.document:
        """Create and return a new empty document tree (root node)."""
        return utils.new_document(self.source.source_path, self.settings)


class ReReader(Reader):

    """
    A reader which rereads an existing document tree (e.g. a
    deserializer).

    Often used in conjunction with `writers.UnfilteredWriter`.
    """

    def get_transforms(self) -> list[type[Transform]]:
        # Do not add any transforms.  They have already been applied
        # by the reader which originally created the document.
        return Component.get_transforms(self)


def get_reader_class(reader_name: str) -> type[Reader]:
    """Return the Reader class from the `reader_name` module."""
    name = reader_name.lower()
    try:
        module = importlib.import_module('docutils.readers.'+name)
    except ImportError:
        try:
            module = importlib.import_module(name)
        except ImportError as err:
            raise ImportError(f'Reader "{reader_name}" not found.') from err
    return module.Reader
