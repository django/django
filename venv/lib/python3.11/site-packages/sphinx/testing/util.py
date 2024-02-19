"""Sphinx test suite utilities"""
from __future__ import annotations

import contextlib
import os
import re
import sys
import warnings
from typing import IO, TYPE_CHECKING, Any
from xml.etree import ElementTree

from docutils import nodes
from docutils.parsers.rst import directives, roles

from sphinx import application, locale
from sphinx.pycode import ModuleAnalyzer

if TYPE_CHECKING:
    from io import StringIO
    from pathlib import Path

    from docutils.nodes import Node

__all__ = 'SphinxTestApp', 'SphinxTestAppWrapperForSkipBuilding'


def assert_node(node: Node, cls: Any = None, xpath: str = "", **kwargs: Any) -> None:
    if cls:
        if isinstance(cls, list):
            assert_node(node, cls[0], xpath=xpath, **kwargs)
            if cls[1:]:
                if isinstance(cls[1], tuple):
                    assert_node(node, cls[1], xpath=xpath, **kwargs)
                else:
                    assert isinstance(node, nodes.Element), \
                        'The node%s does not have any children' % xpath
                    assert len(node) == 1, \
                        'The node%s has %d child nodes, not one' % (xpath, len(node))
                    assert_node(node[0], cls[1:], xpath=xpath + "[0]", **kwargs)
        elif isinstance(cls, tuple):
            assert isinstance(node, (list, nodes.Element)), \
                'The node%s does not have any items' % xpath
            assert len(node) == len(cls), \
                'The node%s has %d child nodes, not %r' % (xpath, len(node), len(cls))
            for i, nodecls in enumerate(cls):
                path = xpath + "[%d]" % i
                assert_node(node[i], nodecls, xpath=path, **kwargs)
        elif isinstance(cls, str):
            assert node == cls, f'The node {xpath!r} is not {cls!r}: {node!r}'
        else:
            assert isinstance(node, cls), \
                f'The node{xpath} is not subclass of {cls!r}: {node!r}'

    if kwargs:
        assert isinstance(node, nodes.Element), \
            'The node%s does not have any attributes' % xpath

        for key, value in kwargs.items():
            if key not in node:
                if (key := key.replace('_', '-')) not in node:
                    msg = f'The node{xpath} does not have {key!r} attribute: {node!r}'
                    raise AssertionError(msg)
            assert node[key] == value, \
                f'The node{xpath}[{key}] is not {value!r}: {node[key]!r}'


def etree_parse(path: str) -> Any:
    with warnings.catch_warnings(record=False):
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        return ElementTree.parse(path)  # NoQA: S314  # using known data in tests


class SphinxTestApp(application.Sphinx):
    """
    A subclass of :class:`Sphinx` that runs on the test root, with some
    better default values for the initialization parameters.
    """
    _status: StringIO
    _warning: StringIO

    def __init__(
        self,
        buildername: str = 'html',
        srcdir: Path | None = None,
        builddir: Path | None = None,
        freshenv: bool = False,
        confoverrides: dict | None = None,
        status: IO | None = None,
        warning: IO | None = None,
        tags: list[str] | None = None,
        docutilsconf: str | None = None,
        parallel: int = 0,
    ) -> None:
        assert srcdir is not None

        self.docutils_conf_path = srcdir / 'docutils.conf'
        if docutilsconf is not None:
            self.docutils_conf_path.write_text(docutilsconf, encoding='utf8')

        if builddir is None:
            builddir = srcdir / '_build'

        confdir = srcdir
        outdir = builddir.joinpath(buildername)
        outdir.mkdir(parents=True, exist_ok=True)
        doctreedir = builddir.joinpath('doctrees')
        doctreedir.mkdir(parents=True, exist_ok=True)
        if confoverrides is None:
            confoverrides = {}
        warningiserror = False

        self._saved_path = sys.path[:]
        self._saved_directives = directives._directives.copy()  # type: ignore[attr-defined]
        self._saved_roles = roles._roles.copy()  # type: ignore[attr-defined]

        self._saved_nodeclasses = {v for v in dir(nodes.GenericNodeVisitor)
                                   if v.startswith('visit_')}

        try:
            super().__init__(srcdir, confdir, outdir, doctreedir,
                             buildername, confoverrides, status, warning,
                             freshenv, warningiserror, tags, parallel=parallel)
        except Exception:
            self.cleanup()
            raise

    def cleanup(self, doctrees: bool = False) -> None:
        ModuleAnalyzer.cache.clear()
        locale.translators.clear()
        sys.path[:] = self._saved_path
        sys.modules.pop('autodoc_fodder', None)
        directives._directives = self._saved_directives  # type: ignore[attr-defined]
        roles._roles = self._saved_roles  # type: ignore[attr-defined]
        for method in dir(nodes.GenericNodeVisitor):
            if method.startswith('visit_') and \
               method not in self._saved_nodeclasses:
                delattr(nodes.GenericNodeVisitor, 'visit_' + method[6:])
                delattr(nodes.GenericNodeVisitor, 'depart_' + method[6:])
        with contextlib.suppress(FileNotFoundError):
            os.remove(self.docutils_conf_path)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} buildername={self.builder.name!r}>'

    def build(self, force_all: bool = False, filenames: list[str] | None = None) -> None:
        self.env._pickled_doctree_cache.clear()
        super().build(force_all, filenames)


class SphinxTestAppWrapperForSkipBuilding:
    """
    This class is a wrapper for SphinxTestApp to speed up the test by skipping
    `app.build` process if it is already built and there is even one output
    file.
    """

    def __init__(self, app_: SphinxTestApp) -> None:
        self.app = app_

    def __getattr__(self, name: str) -> Any:
        return getattr(self.app, name)

    def build(self, *args: Any, **kwargs: Any) -> None:
        if not os.listdir(self.app.outdir):
            # if listdir is empty, do build.
            self.app.build(*args, **kwargs)
            # otherwise, we can use built cache


def strip_escseq(text: str) -> str:
    return re.sub('\x1b.*?m', '', text)
