# $Id: __init__.py 9368 2023-04-28 21:26:36Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils Writer modules.
"""

__docformat__ = 'reStructuredText'

from importlib import import_module

import docutils
from docutils import languages, Component
from docutils.transforms import universal


class Writer(Component):

    """
    Abstract base class for docutils Writers.

    Each writer module or package must export a subclass also called 'Writer'.
    Each writer must support all standard node types listed in
    `docutils.nodes.node_class_names`.

    The `write()` method is the main entry point.
    """

    component_type = 'writer'
    config_section = 'writers'

    def get_transforms(self):
        return super().get_transforms() + [universal.Messages,
                                           universal.FilterMessages,
                                           universal.StripClassesAndElements]

    document = None
    """The document to write (Docutils doctree); set by `write()`."""

    output = None
    """Final translated form of `document`

    (`str` for text, `bytes` for binary formats); set by `translate()`.
    """

    language = None
    """Language module for the document; set by `write()`."""

    destination = None
    """`docutils.io` Output object; where to write the document.

    Set by `write()`.
    """

    def __init__(self):

        self.parts = {}
        """Mapping of document part names to fragments of `self.output`.

        See `Writer.assemble_parts()` below and
        <https://docutils.sourceforge.io/docs/api/publisher.html>.
        """

    def write(self, document, destination):
        """
        Process a document into its final form.

        Translate `document` (a Docutils document tree) into the Writer's
        native format, and write it out to its `destination` (a
        `docutils.io.Output` subclass object).

        Normally not overridden or extended in subclasses.
        """
        self.document = document
        self.language = languages.get_language(
            document.settings.language_code,
            document.reporter)
        self.destination = destination
        self.translate()
        return self.destination.write(self.output)

    def translate(self):
        """
        Do final translation of `self.document` into `self.output`.  Called
        from `write`.  Override in subclasses.

        Usually done with a `docutils.nodes.NodeVisitor` subclass, in
        combination with a call to `docutils.nodes.Node.walk()` or
        `docutils.nodes.Node.walkabout()`.  The ``NodeVisitor`` subclass must
        support all standard elements (listed in
        `docutils.nodes.node_class_names`) and possibly non-standard elements
        used by the current Reader as well.
        """
        raise NotImplementedError('subclass must override this method')

    def assemble_parts(self):
        """Assemble the `self.parts` dictionary.  Extend in subclasses.

        See <https://docutils.sourceforge.io/docs/api/publisher.html>.
        """
        self.parts['whole'] = self.output
        self.parts['encoding'] = self.document.settings.output_encoding
        self.parts['errors'] = (
            self.document.settings.output_encoding_error_handler)
        self.parts['version'] = docutils.__version__


class UnfilteredWriter(Writer):

    """
    A writer that passes the document tree on unchanged (e.g. a
    serializer.)

    Documents written by UnfilteredWriters are typically reused at a
    later date using a subclass of `readers.ReReader`.
    """

    def get_transforms(self):
        # Do not add any transforms.  When the document is reused
        # later, the then-used writer will add the appropriate
        # transforms.
        return Component.get_transforms(self)


_writer_aliases = {
      'html': 'html4css1',  # may change to html5 some day
      'html4': 'html4css1',
      'xhtml10': 'html4css1',
      'html5': 'html5_polyglot',
      'xhtml': 'html5_polyglot',
      's5': 's5_html',
      'latex': 'latex2e',
      'xelatex': 'xetex',
      'luatex': 'xetex',
      'lualatex': 'xetex',
      'odf': 'odf_odt',
      'odt': 'odf_odt',
      'ooffice': 'odf_odt',
      'openoffice': 'odf_odt',
      'libreoffice': 'odf_odt',
      'pprint': 'pseudoxml',
      'pformat': 'pseudoxml',
      'pdf': 'rlpdf',
      'xml': 'docutils_xml'}


def get_writer_class(writer_name):
    """Return the Writer class from the `writer_name` module."""
    name = writer_name.lower()
    name = _writer_aliases.get(name, name)
    try:
        module = import_module('docutils.writers.'+name)
    except ImportError:
        try:
            module = import_module(name)
        except ImportError as err:
            raise ImportError(f'Writer "{writer_name}" not found. {err}')
    return module.Writer
