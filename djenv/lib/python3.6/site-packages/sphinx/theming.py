# -*- coding: utf-8 -*-
"""
    sphinx.theming
    ~~~~~~~~~~~~~~

    Theming support for HTML builders.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
import shutil
import tempfile
import warnings
from os import path
from zipfile import ZipFile

import pkg_resources
from six import string_types, iteritems
from six.moves import configparser

from sphinx import package_dir
from sphinx.deprecation import RemovedInSphinx20Warning
from sphinx.errors import ThemeError
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.osutil import ensuredir

logger = logging.getLogger(__name__)

if False:
    # For type annotation
    from typing import Any, Dict, Iterator, List, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA

NODEFAULT = object()
THEMECONF = 'theme.conf'


def extract_zip(filename, targetdir):
    # type: (unicode, unicode) -> None
    """Extract zip file to target directory."""
    ensuredir(targetdir)

    with ZipFile(filename) as archive:
        for name in archive.namelist():
            if name.endswith('/'):
                continue
            entry = path.join(targetdir, name)
            ensuredir(path.dirname(entry))
            with open(path.join(entry), 'wb') as fp:
                fp.write(archive.read(name))


class Theme(object):
    """A Theme is a set of HTML templates and configurations.

    This class supports both theme directory and theme archive (zipped theme)."""

    def __init__(self, name, theme_path, factory):
        # type: (unicode, unicode, HTMLThemeFactory) -> None
        self.name = name
        self.base = None
        self.rootdir = None

        if path.isdir(theme_path):
            # already a directory, do nothing
            self.rootdir = None
            self.themedir = theme_path
        else:
            # extract the theme to a temp directory
            self.rootdir = tempfile.mkdtemp('sxt')
            self.themedir = path.join(self.rootdir, name)
            extract_zip(theme_path, self.themedir)

        self.config = configparser.RawConfigParser()
        self.config.read(path.join(self.themedir, THEMECONF))  # type: ignore

        try:
            inherit = self.config.get('theme', 'inherit')
        except configparser.NoSectionError:
            raise ThemeError(__('theme %r doesn\'t have "theme" setting') % name)
        except configparser.NoOptionError:
            raise ThemeError(__('theme %r doesn\'t have "inherit" setting') % name)

        if inherit != 'none':
            try:
                self.base = factory.create(inherit)
            except ThemeError:
                raise ThemeError(__('no theme named %r found, inherited by %r') %
                                 (inherit, name))

    def get_theme_dirs(self):
        # type: () -> List[unicode]
        """Return a list of theme directories, beginning with this theme's,
        then the base theme's, then that one's base theme's, etc.
        """
        if self.base is None:
            return [self.themedir]
        else:
            return [self.themedir] + self.base.get_theme_dirs()

    def get_config(self, section, name, default=NODEFAULT):
        # type: (unicode, unicode, Any) -> Any
        """Return the value for a theme configuration setting, searching the
        base theme chain.
        """
        try:
            return self.config.get(section, name)  # type: ignore
        except (configparser.NoOptionError, configparser.NoSectionError):
            if self.base:
                return self.base.get_config(section, name, default)

            if default is NODEFAULT:
                raise ThemeError(__('setting %s.%s occurs in none of the '
                                    'searched theme configs') % (section, name))
            else:
                return default

    def get_options(self, overrides={}):
        # type: (Dict[unicode, Any]) -> Dict[unicode, Any]
        """Return a dictionary of theme options and their values."""
        if self.base:
            options = self.base.get_options()
        else:
            options = {}

        try:
            options.update(self.config.items('options'))
        except configparser.NoSectionError:
            pass

        for option, value in iteritems(overrides):
            if option not in options:
                logger.warning(__('unsupported theme option %r given') % option)
            else:
                options[option] = value

        return options

    def cleanup(self):
        # type: () -> None
        """Remove temporary directories."""
        if self.rootdir:
            try:
                shutil.rmtree(self.rootdir)
            except Exception:
                pass
        if self.base:
            self.base.cleanup()


def is_archived_theme(filename):
    # type: (unicode) -> bool
    """Check the specified file is an archived theme file or not."""
    try:
        with ZipFile(filename) as f:
            return THEMECONF in f.namelist()
    except Exception:
        return False


class HTMLThemeFactory(object):
    """A factory class for HTML Themes."""

    def __init__(self, app):
        # type: (Sphinx) -> None
        self.app = app
        self.themes = app.html_themes
        self.load_builtin_themes()
        if getattr(app.config, 'html_theme_path', None):
            self.load_additional_themes(app.config.html_theme_path)

    def load_builtin_themes(self):
        # type: () -> None
        """Load built-in themes."""
        themes = self.find_themes(path.join(package_dir, 'themes'))
        for name, theme in iteritems(themes):
            self.themes[name] = theme

    def load_additional_themes(self, theme_paths):
        # type: (unicode) -> None
        """Load additional themes placed at specified directories."""
        for theme_path in theme_paths:
            abs_theme_path = path.abspath(path.join(self.app.confdir, theme_path))
            themes = self.find_themes(abs_theme_path)
            for name, theme in iteritems(themes):
                self.themes[name] = theme

    def load_extra_theme(self, name):
        # type: (unicode) -> None
        """Try to load a theme having specifed name."""
        if name == 'alabaster':
            self.load_alabaster_theme()
        elif name == 'sphinx_rtd_theme':
            self.load_sphinx_rtd_theme()
        else:
            self.load_external_theme(name)

    def load_alabaster_theme(self):
        # type: () -> None
        """Load alabaster theme."""
        import alabaster
        self.themes['alabaster'] = path.join(alabaster.get_path(), 'alabaster')

    def load_sphinx_rtd_theme(self):
        # type: () -> None
        """Load sphinx_rtd_theme theme (if exists)."""
        try:
            import sphinx_rtd_theme
            theme_path = sphinx_rtd_theme.get_html_theme_path()
            self.themes['sphinx_rtd_theme'] = path.join(theme_path, 'sphinx_rtd_theme')
        except ImportError:
            pass

    def load_external_theme(self, name):
        # type: (unicode) -> None
        """Try to load a theme using entry_points.

        Sphinx refers to ``sphinx_themes`` entry_points.
        """
        # look up for new styled entry_points at first
        entry_points = pkg_resources.iter_entry_points('sphinx.html_themes', name)
        try:
            entry_point = next(entry_points)
            self.app.registry.load_extension(self.app, entry_point.module_name)
            return
        except StopIteration:
            pass

        # look up for old styled entry_points
        for entry_point in pkg_resources.iter_entry_points('sphinx_themes'):
            target = entry_point.load()
            if callable(target):
                themedir = target()
                if not isinstance(themedir, string_types):
                    logger.warning(__('Theme extension %r does not respond correctly.') %
                                   entry_point.module_name)
            else:
                themedir = target

            themes = self.find_themes(themedir)
            for entry, theme in iteritems(themes):
                if name == entry:
                    warnings.warn('``sphinx_themes`` entry point is now deprecated. '
                                  'Please use ``sphinx.html_themes`` instead.',
                                  RemovedInSphinx20Warning)
                    self.themes[name] = theme

    def find_themes(self, theme_path):
        # type: (unicode) -> Dict[unicode, unicode]
        """Search themes from specified directory."""
        themes = {}  # type: Dict[unicode, unicode]
        if not path.isdir(theme_path):
            return themes

        for entry in os.listdir(theme_path):
            pathname = path.join(theme_path, entry)
            if path.isfile(pathname) and entry.lower().endswith('.zip'):
                if is_archived_theme(pathname):
                    name = entry[:-4]
                    themes[name] = pathname
                else:
                    logger.warning(__('file %r on theme path is not a valid '
                                      'zipfile or contains no theme'), entry)
            else:
                if path.isfile(path.join(pathname, THEMECONF)):
                    themes[entry] = pathname

        return themes

    def create(self, name):
        # type: (unicode) -> Theme
        """Create an instance of theme."""
        if name not in self.themes:
            self.load_extra_theme(name)

        if name not in self.themes:
            if name == 'sphinx_rtd_theme':
                raise ThemeError(__('sphinx_rtd_theme is no longer a hard dependency '
                                    'since version 1.4.0. Please install it manually.'
                                    '(pip install sphinx_rtd_theme)'))
            else:
                raise ThemeError(__('no theme named %r found '
                                    '(missing theme.conf?)') % name)

        return Theme(name, self.themes[name], factory=self)
