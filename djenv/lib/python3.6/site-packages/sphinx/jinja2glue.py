# -*- coding: utf-8 -*-
"""
    sphinx.jinja2glue
    ~~~~~~~~~~~~~~~~~

    Glue code for the jinja2 templating engine.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from os import path
from pprint import pformat
from typing import Any, Callable, Iterator, Tuple  # NOQA

from jinja2 import FileSystemLoader, BaseLoader, TemplateNotFound, \
    contextfunction
from jinja2.sandbox import SandboxedEnvironment
from jinja2.utils import open_if_exists
from six import string_types

from sphinx.application import TemplateBridge
from sphinx.util import logging
from sphinx.util.osutil import mtimes_of_files

if False:
    # For type annotation
    from typing import Any, Callable, Dict, List, Iterator, Tuple, Union  # NOQA
    from jinja2.environment import Environment  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.theming import Theme  # NOQA


def _tobool(val):
    # type: (unicode) -> bool
    if isinstance(val, string_types):
        return val.lower() in ('true', '1', 'yes', 'on')
    return bool(val)


def _toint(val):
    # type: (unicode) -> int
    try:
        return int(val)
    except ValueError:
        return 0


def _todim(val):
    # type: (Union[int, unicode]) -> unicode
    """
    Make val a css dimension. In particular the following transformations
    are performed:

    - None -> 'initial' (default CSS value)
    - 0 -> '0'
    - ints and string representations of ints are interpreted as pixels.

    Everything else is returned unchanged.
    """
    if val is None:
        return 'initial'
    elif str(val).isdigit():
        return '0' if int(val) == 0 else '%spx' % val
    return val  # type: ignore


def _slice_index(values, slices):
    # type: (List, int) -> Iterator[List]
    seq = list(values)
    length = 0
    for value in values:
        length += 1 + len(value[1][1])  # count includes subitems
    items_per_slice = length // slices
    offset = 0
    for slice_number in range(slices):
        count = 0
        start = offset
        if slices == slice_number + 1:  # last column
            offset = len(seq)
        else:
            for value in values[offset:]:
                count += 1 + len(value[1][1])
                offset += 1
                if count >= items_per_slice:
                    break
        yield seq[start:offset]


def accesskey(context, key):
    # type: (Any, unicode) -> unicode
    """Helper to output each access key only once."""
    if '_accesskeys' not in context:
        context.vars['_accesskeys'] = {}
    if key and key not in context.vars['_accesskeys']:
        context.vars['_accesskeys'][key] = 1
        return 'accesskey="%s"' % key
    return ''


class idgen(object):
    def __init__(self):
        # type: () -> None
        self.id = 0

    def current(self):
        # type: () -> int
        return self.id

    def __next__(self):
        # type: () -> int
        self.id += 1
        return self.id
    next = __next__  # Python 2/Jinja compatibility


@contextfunction
def warning(context, message, *args, **kwargs):
    # type: (Dict, unicode, Any, Any) -> unicode
    if 'pagename' in context:
        filename = context.get('pagename') + context.get('file_suffix', '')
        message = 'in rendering %s: %s' % (filename, message)
    logger = logging.getLogger('sphinx.themes')
    logger.warning(message, *args, **kwargs)
    return ''  # return empty string not to output any values


class SphinxFileSystemLoader(FileSystemLoader):
    """
    FileSystemLoader subclass that is not so strict about '..'  entries in
    template names.
    """

    def get_source(self, environment, template):
        # type: (Environment, unicode) -> Tuple[unicode, unicode, Callable]
        for searchpath in self.searchpath:
            filename = path.join(searchpath, template)
            f = open_if_exists(filename)
            if f is None:
                continue
            with f:
                contents = f.read().decode(self.encoding)

            mtime = path.getmtime(filename)

            def uptodate():
                # type: () -> bool
                try:
                    return path.getmtime(filename) == mtime
                except OSError:
                    return False
            return contents, filename, uptodate
        raise TemplateNotFound(template)


class BuiltinTemplateLoader(TemplateBridge, BaseLoader):
    """
    Interfaces the rendering environment of jinja2 for use in Sphinx.
    """

    # TemplateBridge interface

    def init(self, builder, theme=None, dirs=None):
        # type: (Builder, Theme, List[unicode]) -> None
        # create a chain of paths to search
        if theme:
            # the theme's own dir and its bases' dirs
            pathchain = theme.get_theme_dirs()
            # the loader dirs: pathchain + the parent directories for all themes
            loaderchain = pathchain + [path.join(p, '..') for p in pathchain]
        elif dirs:
            pathchain = list(dirs)
            loaderchain = list(dirs)
        else:
            pathchain = []
            loaderchain = []

        # prepend explicit template paths
        self.templatepathlen = len(builder.config.templates_path)
        if builder.config.templates_path:
            cfg_templates_path = [path.join(builder.confdir, tp)
                                  for tp in builder.config.templates_path]
            pathchain[0:0] = cfg_templates_path
            loaderchain[0:0] = cfg_templates_path

        # store it for use in newest_template_mtime
        self.pathchain = pathchain

        # make the paths into loaders
        self.loaders = [SphinxFileSystemLoader(x) for x in loaderchain]

        use_i18n = builder.app.translator is not None
        extensions = use_i18n and ['jinja2.ext.i18n'] or []
        self.environment = SandboxedEnvironment(loader=self,
                                                extensions=extensions)
        self.environment.filters['tobool'] = _tobool
        self.environment.filters['toint'] = _toint
        self.environment.filters['todim'] = _todim
        self.environment.filters['slice_index'] = _slice_index
        self.environment.globals['debug'] = contextfunction(pformat)
        self.environment.globals['warning'] = warning
        self.environment.globals['accesskey'] = contextfunction(accesskey)
        self.environment.globals['idgen'] = idgen
        if use_i18n:
            self.environment.install_gettext_translations(builder.app.translator)  # type: ignore  # NOQA

    def render(self, template, context):  # type: ignore
        # type: (unicode, Dict) -> unicode
        return self.environment.get_template(template).render(context)

    def render_string(self, source, context):
        # type: (unicode, Dict) -> unicode
        return self.environment.from_string(source).render(context)

    def newest_template_mtime(self):
        # type: () -> float
        return max(mtimes_of_files(self.pathchain, '.html'))

    # Loader interface

    def get_source(self, environment, template):
        # type: (Environment, unicode) -> Tuple[unicode, unicode, Callable]
        loaders = self.loaders
        # exclamation mark starts search from theme
        if template.startswith('!'):
            loaders = loaders[self.templatepathlen:]
            template = template[1:]
        for loader in loaders:
            try:
                return loader.get_source(environment, template)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(template)
