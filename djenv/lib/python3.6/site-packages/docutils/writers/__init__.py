# $Id: __init__.py 7969 2016-08-18 21:40:00Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils Writer modules.
"""

__docformat__ = 'reStructuredText'

import os.path
import sys

import docutils
from docutils import languages, Component
from docutils.transforms import universal
if sys.version_info < (2,5):
    from docutils._compat import __import__


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
        return Component.get_transforms(self) + [
            universal.Messages,
            universal.FilterMessages,
            universal.StripClassesAndElements,]

    document = None
    """The document to write (Docutils doctree); set by `write`."""

    output = None
    """Final translated form of `document` (Unicode string for text, binary
    string for other forms); set by `translate`."""

    language = None
    """Language module for the document; set by `write`."""

    destination = None
    """`docutils.io` Output object; where to write the document.
    Set by `write`."""

    def __init__(self):

        # Used by HTML and LaTeX writer for output fragments:
        self.parts = {}
        """Mapping of document part names to fragments of `self.output`.
        Values are Unicode strings; encoding is up to the client.  The 'whole'
        key should contain the entire document output.
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
        output = self.destination.write(self.output)
        return output

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
        """Assemble the `self.parts` dictionary.  Extend in subclasses."""
        self.parts['whole'] = self.output
        self.parts['encoding'] = self.document.settings.output_encoding
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
      'html5': 'html5_polyglot',
      'latex': 'latex2e',
      'pprint': 'pseudoxml',
      'pformat': 'pseudoxml',
      'pdf': 'rlpdf',
      's5': 's5_html',
      'xelatex': 'xetex',
      'xhtml': 'html5_polyglot',
      'xhtml10': 'html4css1',
      'xml': 'docutils_xml'}

def get_writer_class(writer_name):
    """Return the Writer class from the `writer_name` module."""
    writer_name = writer_name.lower()
    if writer_name in _writer_aliases:
        writer_name = _writer_aliases[writer_name]
    try:
        module = __import__(writer_name, globals(), locals(), level=1)
    except ImportError:
        module = __import__(writer_name, globals(), locals(), level=0)
    return module.Writer
