"""Templates utility functions for Sphinx."""

from __future__ import annotations

import os
from functools import partial
from os import path
from typing import TYPE_CHECKING, Any, Callable

from jinja2 import TemplateNotFound
from jinja2.loaders import BaseLoader
from jinja2.sandbox import SandboxedEnvironment

from sphinx import package_dir
from sphinx.jinja2glue import SphinxFileSystemLoader
from sphinx.locale import get_translator
from sphinx.util import rst, texescape

if TYPE_CHECKING:
    from collections.abc import Sequence

    from jinja2.environment import Environment


class BaseRenderer:
    def __init__(self, loader: BaseLoader | None = None) -> None:
        self.env = SandboxedEnvironment(loader=loader, extensions=['jinja2.ext.i18n'])
        self.env.filters['repr'] = repr
        self.env.install_gettext_translations(get_translator())

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        return self.env.get_template(template_name).render(context)

    def render_string(self, source: str, context: dict[str, Any]) -> str:
        return self.env.from_string(source).render(context)


class FileRenderer(BaseRenderer):
    def __init__(self, search_path: Sequence[str | os.PathLike[str]]) -> None:
        if isinstance(search_path, (str, os.PathLike)):
            search_path = [search_path]
        else:
            # filter "None" paths
            search_path = list(filter(None, search_path))

        loader = SphinxFileSystemLoader(search_path)
        super().__init__(loader)

    @classmethod
    def render_from_file(cls, filename: str, context: dict[str, Any]) -> str:
        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        return cls(dirname).render(basename, context)


class SphinxRenderer(FileRenderer):
    def __init__(self, template_path: Sequence[str | os.PathLike[str]] | None = None) -> None:
        if template_path is None:
            template_path = os.path.join(package_dir, 'templates')
        super().__init__(template_path)

    @classmethod
    def render_from_file(cls, filename: str, context: dict[str, Any]) -> str:
        return FileRenderer.render_from_file(filename, context)


class LaTeXRenderer(SphinxRenderer):
    def __init__(self, template_path: Sequence[str | os.PathLike[str]] | None = None,
                 latex_engine: str | None = None) -> None:
        if template_path is None:
            template_path = [os.path.join(package_dir, 'templates', 'latex')]
        super().__init__(template_path)

        # use texescape as escape filter
        escape = partial(texescape.escape, latex_engine=latex_engine)
        self.env.filters['e'] = escape
        self.env.filters['escape'] = escape
        self.env.filters['eabbr'] = texescape.escape_abbr

        # use JSP/eRuby like tagging instead because curly bracket; the default
        # tagging of jinja2 is not good for LaTeX sources.
        self.env.variable_start_string = '<%='
        self.env.variable_end_string = '%>'
        self.env.block_start_string = '<%'
        self.env.block_end_string = '%>'
        self.env.comment_start_string = '<#'
        self.env.comment_end_string = '#>'


class ReSTRenderer(SphinxRenderer):
    def __init__(self, template_path: Sequence[str | os.PathLike[str]] | None = None,
                 language: str | None = None) -> None:
        super().__init__(template_path)

        # add language to environment
        self.env.extend(language=language)

        # use texescape as escape filter
        self.env.filters['e'] = rst.escape
        self.env.filters['escape'] = rst.escape
        self.env.filters['heading'] = rst.heading


class SphinxTemplateLoader(BaseLoader):
    """A loader supporting template inheritance"""

    def __init__(self, confdir: str | os.PathLike[str],
                 templates_paths: Sequence[str | os.PathLike[str]],
                 system_templates_paths: Sequence[str | os.PathLike[str]]) -> None:
        self.loaders = []
        self.sysloaders = []

        for templates_path in templates_paths:
            loader = SphinxFileSystemLoader(path.join(confdir, templates_path))
            self.loaders.append(loader)

        for templates_path in system_templates_paths:
            loader = SphinxFileSystemLoader(templates_path)
            self.loaders.append(loader)
            self.sysloaders.append(loader)

    def get_source(self, environment: Environment, template: str) -> tuple[str, str, Callable]:
        if template.startswith('!'):
            # search a template from ``system_templates_paths``
            loaders = self.sysloaders
            template = template[1:]
        else:
            loaders = self.loaders

        for loader in loaders:
            try:
                return loader.get_source(environment, template)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(template)
