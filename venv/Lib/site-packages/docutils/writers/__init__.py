# $Id: __init__.py 10045 2025-03-09 01:02:23Z aa-turner $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This package contains Docutils Writer modules.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import importlib
import sys
import urllib
from pathlib import Path

import docutils
from docutils import Component, languages, nodes, utils
from docutils.transforms import universal

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any, Final

    from docutils.io import Output
    from docutils.languages import LanguageModule
    from docutils.nodes import StrPath
    from docutils.transforms import Transform


class Writer(Component):

    """
    Abstract base class for docutils Writers.

    Each writer module or package must export a subclass also called 'Writer'.
    Each writer must support all standard node types listed in
    `docutils.nodes.node_class_names`.

    The `write()` method is the main entry point.
    """

    component_type: Final = 'writer'
    config_section: Final = 'writers'

    def get_transforms(self) -> list[type[Transform]]:
        return super().get_transforms() + [universal.Messages,
                                           universal.FilterMessages,
                                           universal.StripClassesAndElements]

    document: nodes.document | None = None
    """The document to write (Docutils doctree); set by `write()`."""

    output: str | bytes | None = None
    """Final translated form of `document`

    (`str` for text, `bytes` for binary formats); set by `translate()`.
    """

    language: LanguageModule | None = None
    """Language module for the document; set by `write()`."""

    destination: Output | None = None
    """`docutils.io` Output object; where to write the document.

    Set by `write()`.
    """

    def __init__(self) -> None:

        self.parts: dict[str, Any] = {}
        """Mapping of document part names to fragments of `self.output`.

        See `Writer.assemble_parts()` below and
        <https://docutils.sourceforge.io/docs/api/publisher.html>.
        """

    def write(self,
              document: nodes.document,
              destination: Output
              ) -> str | bytes | None:
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

    def translate(self) -> None:
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

    def assemble_parts(self) -> None:
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

    def get_transforms(self) -> list[type[Transform]]:
        # Do not add any transforms.  When the document is reused
        # later, the then-used writer will add the appropriate
        # transforms.
        return Component.get_transforms(self)


class DoctreeTranslator(nodes.NodeVisitor):
    """
    Generic Docutils document tree translator base class.

    Adds auxiliary methods and attributes that are used by several
    Docutils writers to the `nodes.NodeVisitor` abstract superclass.
    """

    def __init__(self, document) -> None:
        super().__init__(document)
        self.settings = document.settings

    def uri2path(self, uri: str, output_path: StrPath|None = None) -> Path:
        """Return filesystem path corresponding to a `URI reference`__.

        The `root_prefix`__ setting` is applied to URI references starting
        with "/" (but not to absolute Windows paths or "file" URIs).

        If `output_path` (defaults to the `output_path`__ setting) is
        not empty, relative paths are adjusted.
        (To work in the output document, URI references with relative path
        relate to the output directory.  For access by the writer, paths
        must be relative to the working directory.)

        Use case:
          The <image> element refers to the image via a "URI reference".
          The corresponding filesystem path is required to read the
          image size from the file or to embed the image in the output.

          A filesystem path is also expected by the "LaTeX" output format
          (with relative paths unchanged, relating to the output directory,
          set `output_path` to the empty string).

        Provisional: the function's location, interface and behaviour
        may change without advance warning.

        __ https://www.rfc-editor.org/rfc/rfc3986.html#section-4.1
        __ https://docutils.sourceforge.io/docs/user/config.html#root-prefix
        __ https://docutils.sourceforge.io/docs/user/config.html#output-path
        """
        if output_path is None:
            output_path = self.settings.output_path
        if uri.startswith('file:'):
            return Path.from_uri(uri)
        uri_parts = urllib.parse.urlsplit(uri)
        if uri_parts.scheme != '':
            raise ValueError(f'Cannot get file path corresponding to {uri}.')
        # extract and adjust path from "relative URI reference"
        path = urllib.parse.unquote(uri_parts.path)
        if self.settings.root_prefix and path.startswith('/'):
            return Path(self.settings.root_prefix) / path.removeprefix('/')
        path = Path(path)
        # adjust relative paths (but not "d:/foo" or similar)
        if output_path and not path.is_absolute():
            dest_dir = Path(output_path).parent.resolve()
            path = Path(utils.relative_path(None, dest_dir/path))
            # TODO: support paths relative to the *source* directory?
            # source_path, line = utils.get_source_line(node)
            # if source_path:
            #     source_dir = Path(source_path).parent.resolve()
            #     path = Path(utils.relative_path(None, source_dir/path)
        return path


if sys.version_info[:2] < (3, 13):
    # Backport `pathlib.Path.from_uri()` class method:
    import pathlib

    # subclassing from Path must consider the OS flavour
    # https://stackoverflow.com/questions/29850801/subclass-pathlib-path-fails
    class Path(type(pathlib.Path())):  # noqa: F811 (redefinition of 'Path')
        """`pathlib.Path` with `from_uri()` classmethod backported from 3.13.
        """

        # `from_uri()` is copied from
        # https://github.com/python/cpython/blob/3.13/Lib/pathlib/_local.py
        # with minor adaptions
        @classmethod
        def from_uri(cls, uri):
            """Return a new path from the given 'file' URI."""
            if not uri.startswith('file:'):
                raise ValueError(f"URI does not start with 'file:': {uri!r}")
            path = uri[5:]
            if path[:3] == '///':
                # Remove empty authority
                path = path[2:]
            elif path[:12] == '//localhost/':
                # Remove 'localhost' authority
                path = path[11:]
            if path[:3] == '///' or (path[:1] == '/' and path[2:3] in ':|'):
                # Remove slash before DOS device/UNC path
                path = path[1:]
            if path[1:2] == '|':
                # Replace bar with colon in DOS drive
                path = path[:1] + ':' + path[2:]
            path = cls(urllib.parse.unquote(path))
            if not path.is_absolute():
                raise ValueError(f"URI is not absolute: {uri!r}")
            return path


WRITER_ALIASES = {'html': 'html4css1',  # will change to html5 in Docutils 2.0
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
                  'xml': 'docutils_xml',
                  }


def get_writer_class(writer_name: str) -> type[Writer]:
    """Return the Writer class from the `writer_name` module."""
    name = writer_name.lower()
    name = WRITER_ALIASES.get(name, name)
    try:
        module = importlib.import_module('docutils.writers.'+name)
    except ImportError:
        try:
            module = importlib.import_module(name)
        except ImportError as err:
            raise ImportError(f'Writer "{writer_name}" not found. {err}')
    return module.Writer
