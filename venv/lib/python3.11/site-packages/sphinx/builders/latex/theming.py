"""Theming support for LaTeX builder."""

from __future__ import annotations

import configparser
from os import path
from typing import TYPE_CHECKING

from sphinx.errors import ThemeError
from sphinx.locale import __
from sphinx.util import logging

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config

logger = logging.getLogger(__name__)


class Theme:
    """A set of LaTeX configurations."""

    LATEX_ELEMENTS_KEYS = ['papersize', 'pointsize']
    UPDATABLE_KEYS = ['papersize', 'pointsize']

    def __init__(self, name: str) -> None:
        self.name = name
        self.docclass = name
        self.wrapperclass = name
        self.papersize = 'letterpaper'
        self.pointsize = '10pt'
        self.toplevel_sectioning = 'chapter'

    def update(self, config: Config) -> None:
        """Override theme settings by user's configuration."""
        for key in self.LATEX_ELEMENTS_KEYS:
            if config.latex_elements.get(key):
                value = config.latex_elements[key]
                setattr(self, key, value)

        for key in self.UPDATABLE_KEYS:
            if key in config.latex_theme_options:
                value = config.latex_theme_options[key]
                setattr(self, key, value)


class BuiltInTheme(Theme):
    """A built-in LaTeX theme."""

    def __init__(self, name: str, config: Config) -> None:
        super().__init__(name)

        if name == 'howto':
            self.docclass = config.latex_docclass.get('howto', 'article')
        else:
            self.docclass = config.latex_docclass.get('manual', 'report')

        if name in ('manual', 'howto'):
            self.wrapperclass = 'sphinx' + name
        else:
            self.wrapperclass = name

        # we assume LaTeX class provides \chapter command except in case
        # of non-Japanese 'howto' case
        if name == 'howto' and not self.docclass.startswith('j'):
            self.toplevel_sectioning = 'section'
        else:
            self.toplevel_sectioning = 'chapter'


class UserTheme(Theme):
    """A user defined LaTeX theme."""

    REQUIRED_CONFIG_KEYS = ['docclass', 'wrapperclass']
    OPTIONAL_CONFIG_KEYS = ['papersize', 'pointsize', 'toplevel_sectioning']

    def __init__(self, name: str, filename: str) -> None:
        super().__init__(name)
        self.config = configparser.RawConfigParser()
        self.config.read(path.join(filename), encoding='utf-8')

        for key in self.REQUIRED_CONFIG_KEYS:
            try:
                value = self.config.get('theme', key)
                setattr(self, key, value)
            except configparser.NoSectionError as exc:
                raise ThemeError(__('%r doesn\'t have "theme" setting') %
                                 filename) from exc
            except configparser.NoOptionError as exc:
                raise ThemeError(__('%r doesn\'t have "%s" setting') %
                                 (filename, exc.args[0])) from exc

        for key in self.OPTIONAL_CONFIG_KEYS:
            try:
                value = self.config.get('theme', key)
                setattr(self, key, value)
            except configparser.NoOptionError:
                pass


class ThemeFactory:
    """A factory class for LaTeX Themes."""

    def __init__(self, app: Sphinx) -> None:
        self.themes: dict[str, Theme] = {}
        self.theme_paths = [path.join(app.srcdir, p) for p in app.config.latex_theme_path]
        self.config = app.config
        self.load_builtin_themes(app.config)

    def load_builtin_themes(self, config: Config) -> None:
        """Load built-in themes."""
        self.themes['manual'] = BuiltInTheme('manual', config)
        self.themes['howto'] = BuiltInTheme('howto', config)

    def get(self, name: str) -> Theme:
        """Get a theme for given *name*."""
        if name in self.themes:
            theme = self.themes[name]
        else:
            theme = self.find_user_theme(name) or Theme(name)

        theme.update(self.config)
        return theme

    def find_user_theme(self, name: str) -> Theme | None:
        """Find a theme named as *name* from latex_theme_path."""
        for theme_path in self.theme_paths:
            config_path = path.join(theme_path, name, 'theme.conf')
            if path.isfile(config_path):
                try:
                    return UserTheme(name, config_path)
                except ThemeError as exc:
                    logger.warning(exc)

        return None
