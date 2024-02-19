"""Utility function and classes for Sphinx projects."""

from __future__ import annotations

import contextlib
import os
from glob import glob
from typing import TYPE_CHECKING

from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.matching import get_matching_files
from sphinx.util.osutil import path_stabilize, relpath

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)
EXCLUDE_PATHS = ['**/_sources', '.#*', '**/.#*', '*.lproj/**']


class Project:
    """A project is the source code set of the Sphinx document(s)."""

    def __init__(self, srcdir: str | os.PathLike[str], source_suffix: Iterable[str]) -> None:
        #: Source directory.
        self.srcdir = srcdir

        #: source_suffix. Same as :confval:`source_suffix`.
        self.source_suffix = tuple(source_suffix)
        self._first_source_suffix = next(iter(self.source_suffix), "")

        #: The name of documents belonging to this project.
        self.docnames: set[str] = set()

        # Bijective mapping between docnames and (srcdir relative) paths.
        self._path_to_docname: dict[str, str] = {}
        self._docname_to_path: dict[str, str] = {}

    def restore(self, other: Project) -> None:
        """Take over a result of last build."""
        self.docnames = other.docnames
        self._path_to_docname = other._path_to_docname
        self._docname_to_path = other._docname_to_path

    def discover(self, exclude_paths: Iterable[str] = (),
                 include_paths: Iterable[str] = ("**",)) -> set[str]:
        """Find all document files in the source directory and put them in
        :attr:`docnames`.
        """

        self.docnames.clear()
        self._path_to_docname.clear()
        self._docname_to_path.clear()

        for filename in get_matching_files(
            self.srcdir,
            include_paths,
            [*exclude_paths] + EXCLUDE_PATHS,
        ):
            if docname := self.path2doc(filename):
                if docname in self.docnames:
                    pattern = os.path.join(self.srcdir, docname) + '.*'
                    files = [relpath(f, self.srcdir) for f in glob(pattern)]
                    logger.warning(__('multiple files found for the document "%s": %r\n'
                                      'Use %r for the build.'),
                                   docname, files, self.doc2path(docname, absolute=True),
                                   once=True)
                elif os.access(os.path.join(self.srcdir, filename), os.R_OK):
                    self.docnames.add(docname)
                    self._path_to_docname[filename] = docname
                    self._docname_to_path[docname] = filename
                else:
                    logger.warning(__("Ignored unreadable document %r."),
                                   filename, location=docname)

        return self.docnames

    def path2doc(self, filename: str | os.PathLike[str]) -> str | None:
        """Return the docname for the filename if the file is a document.

        *filename* should be absolute or relative to the source directory.
        """
        try:
            return self._path_to_docname[filename]  # type: ignore[index]
        except KeyError:
            if os.path.isabs(filename):
                with contextlib.suppress(ValueError):
                    filename = os.path.relpath(filename, self.srcdir)

            for suffix in self.source_suffix:
                if os.path.basename(filename).endswith(suffix):
                    return path_stabilize(filename).removesuffix(suffix)

            # the file does not have a docname
            return None

    def doc2path(self, docname: str, absolute: bool) -> str:
        """Return the filename for the document name.

        If *absolute* is True, return as an absolute path.
        Else, return as a relative path to the source directory.
        """
        try:
            filename = self._docname_to_path[docname]
        except KeyError:
            # Backwards compatibility: the document does not exist
            filename = docname + self._first_source_suffix

        if absolute:
            return os.path.join(self.srcdir, filename)
        return filename
