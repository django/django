"""Utilities parsing and analyzing Python code."""

from __future__ import annotations

import tokenize
from importlib import import_module
from os import path
from typing import TYPE_CHECKING, Any

from sphinx.errors import PycodeError
from sphinx.pycode.parser import Parser

if TYPE_CHECKING:
    from inspect import Signature


class ModuleAnalyzer:
    annotations: dict[tuple[str, str], str]
    attr_docs: dict[tuple[str, str], list[str]]
    finals: list[str]
    overloads: dict[str, list[Signature]]
    tagorder: dict[str, int]
    tags: dict[str, tuple[str, int, int]]

    # cache for analyzer objects -- caches both by module and file name
    cache: dict[tuple[str, str], Any] = {}

    @staticmethod
    def get_module_source(modname: str) -> tuple[str | None, str | None]:
        """Try to find the source code for a module.

        Returns ('filename', 'source'). One of it can be None if
        no filename or source found
        """
        try:
            mod = import_module(modname)
        except Exception as err:
            raise PycodeError('error importing %r' % modname, err) from err
        loader = getattr(mod, '__loader__', None)
        filename = getattr(mod, '__file__', None)
        if loader and getattr(loader, 'get_source', None):
            # prefer Native loader, as it respects #coding directive
            try:
                source = loader.get_source(modname)
                if source:
                    # no exception and not None - it must be module source
                    return filename, source
            except ImportError:
                pass  # Try other "source-mining" methods
        if filename is None and loader and getattr(loader, 'get_filename', None):
            # have loader, but no filename
            try:
                filename = loader.get_filename(modname)
            except ImportError as err:
                raise PycodeError('error getting filename for %r' % modname, err) from err
        if filename is None:
            # all methods for getting filename failed, so raise...
            raise PycodeError('no source found for module %r' % modname)
        filename = path.normpath(path.abspath(filename))
        if filename.lower().endswith(('.pyo', '.pyc')):
            filename = filename[:-1]
            if not path.isfile(filename) and path.isfile(filename + 'w'):
                filename += 'w'
        elif not filename.lower().endswith(('.py', '.pyw')):
            raise PycodeError('source is not a .py file: %r' % filename)

        if not path.isfile(filename):
            raise PycodeError('source file is not present: %r' % filename)
        return filename, None

    @classmethod
    def for_string(cls, string: str, modname: str, srcname: str = '<string>',
                   ) -> ModuleAnalyzer:
        return cls(string, modname, srcname)

    @classmethod
    def for_file(cls, filename: str, modname: str) -> ModuleAnalyzer:
        if ('file', filename) in cls.cache:
            return cls.cache['file', filename]
        try:
            with tokenize.open(filename) as f:
                string = f.read()
            obj = cls(string, modname, filename)
            cls.cache['file', filename] = obj
        except Exception as err:
            raise PycodeError('error opening %r' % filename, err) from err
        return obj

    @classmethod
    def for_module(cls, modname: str) -> ModuleAnalyzer:
        if ('module', modname) in cls.cache:
            entry = cls.cache['module', modname]
            if isinstance(entry, PycodeError):
                raise entry
            return entry

        try:
            filename, source = cls.get_module_source(modname)
            if source is not None:
                obj = cls.for_string(source, modname, filename or '<string>')
            elif filename is not None:
                obj = cls.for_file(filename, modname)
        except PycodeError as err:
            cls.cache['module', modname] = err
            raise
        cls.cache['module', modname] = obj
        return obj

    def __init__(self, source: str, modname: str, srcname: str) -> None:
        self.modname = modname  # name of the module
        self.srcname = srcname  # name of the source file

        # cache the source code as well
        self.code = source

        self._analyzed = False

    def analyze(self) -> None:
        """Analyze the source code."""
        if self._analyzed:
            return

        try:
            parser = Parser(self.code)
            parser.parse()

            self.attr_docs = {}
            for (scope, comment) in parser.comments.items():
                if comment:
                    self.attr_docs[scope] = comment.splitlines() + ['']
                else:
                    self.attr_docs[scope] = ['']

            self.annotations = parser.annotations
            self.finals = parser.finals
            self.overloads = parser.overloads
            self.tags = parser.definitions
            self.tagorder = parser.deforders
            self._analyzed = True
        except Exception as exc:
            msg = f'parsing {self.srcname!r} failed: {exc!r}'
            raise PycodeError(msg) from exc

    def find_attr_docs(self) -> dict[tuple[str, str], list[str]]:
        """Find class and module-level attributes and their documentation."""
        self.analyze()
        return self.attr_docs

    def find_tags(self) -> dict[str, tuple[str, int, int]]:
        """Find class, function and method definitions and their location."""
        self.analyze()
        return self.tags
