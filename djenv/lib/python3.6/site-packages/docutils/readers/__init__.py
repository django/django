# $Id: __init__.py 7648 2013-04-18 07:36:22Z milde $
# Authors: David Goodger <goodger@python.org>; Ueli Schlaepfer
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils Reader modules.
"""

__docformat__ = 'reStructuredText'

import sys

from docutils import utils, parsers, Component
from docutils.transforms import universal
if sys.version_info < (2,5):
    from docutils._compat import __import__


class Reader(Component):

    """
    Abstract base class for docutils Readers.

    Each reader module or package must export a subclass also called 'Reader'.

    The two steps of a Reader's responsibility are `scan()` and
    `parse()`.  Call `read()` to process a document.
    """

    component_type = 'reader'
    config_section = 'readers'

    def get_transforms(self):
        return Component.get_transforms(self) + [
            universal.Decorations,
            universal.ExposeInternals,
            universal.StripComments,]

    def __init__(self, parser=None, parser_name=None):
        """
        Initialize the Reader instance.

        Several instance attributes are defined with dummy initial values.
        Subclasses may use these attributes as they wish.
        """

        self.parser = parser
        """A `parsers.Parser` instance shared by all doctrees.  May be left
        unspecified if the document source determines the parser."""

        if parser is None and parser_name:
            self.set_parser(parser_name)

        self.source = None
        """`docutils.io` IO object, source of input data."""

        self.input = None
        """Raw text input; either a single string or, for more complex cases,
        a collection of strings."""

    def set_parser(self, parser_name):
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

    def parse(self):
        """Parse `self.input` into a document tree."""
        self.document = document = self.new_document()
        self.parser.parse(self.input, document)
        document.current_source = document.current_line = None

    def new_document(self):
        """Create and return a new empty document tree (root node)."""
        document = utils.new_document(self.source.source_path, self.settings)
        return document


class ReReader(Reader):

    """
    A reader which rereads an existing document tree (e.g. a
    deserializer).

    Often used in conjunction with `writers.UnfilteredWriter`.
    """

    def get_transforms(self):
        # Do not add any transforms.  They have already been applied
        # by the reader which originally created the document.
        return Component.get_transforms(self)


_reader_aliases = {}

def get_reader_class(reader_name):
    """Return the Reader class from the `reader_name` module."""
    reader_name = reader_name.lower()
    if reader_name in _reader_aliases:
        reader_name = _reader_aliases[reader_name]
    try:
        module = __import__(reader_name, globals(), locals(), level=1)
    except ImportError:
        module = __import__(reader_name, globals(), locals(), level=0)
    return module.Reader
