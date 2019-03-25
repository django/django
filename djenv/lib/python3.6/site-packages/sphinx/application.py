# -*- coding: utf-8 -*-
"""
    sphinx.application
    ~~~~~~~~~~~~~~~~~~

    Sphinx application class and extensibility interface.

    Gracefully adapted from the TextPress system by Armin.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import print_function

import os
import sys
import warnings
from collections import deque
from inspect import isclass
from os import path

from docutils.parsers.rst import Directive, directives, roles
from six import itervalues
from six.moves import cPickle as pickle
from six.moves import cStringIO

import sphinx
from sphinx import package_dir, locale
from sphinx.config import Config, check_unicode
from sphinx.config import CONFIG_FILENAME  # NOQA # for compatibility (RemovedInSphinx30)
from sphinx.deprecation import (
    RemovedInSphinx20Warning, RemovedInSphinx30Warning, RemovedInSphinx40Warning
)
from sphinx.environment import BuildEnvironment
from sphinx.errors import ApplicationError, ConfigError, VersionRequirementError
from sphinx.events import EventManager
from sphinx.locale import __
from sphinx.registry import SphinxComponentRegistry
from sphinx.util import docutils
from sphinx.util import import_object
from sphinx.util import logging
from sphinx.util import pycompat  # noqa: F401
from sphinx.util.build_phase import BuildPhase
from sphinx.util.console import bold  # type: ignore
from sphinx.util.docutils import directive_helper
from sphinx.util.i18n import find_catalog_source_files
from sphinx.util.osutil import abspath, ensuredir, relpath
from sphinx.util.tags import Tags

if False:
    # For type annotation
    from typing import Any, Callable, Dict, IO, Iterable, Iterator, List, Tuple, Type, Union  # NOQA
    from docutils import nodes  # NOQA
    from docutils.parsers import Parser  # NOQA
    from docutils.transforms import Transform  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.domains import Domain, Index  # NOQA
    from sphinx.environment.collectors import EnvironmentCollector  # NOQA
    from sphinx.extension import Extension  # NOQA
    from sphinx.roles import XRefRole  # NOQA
    from sphinx.theming import Theme  # NOQA
    from sphinx.util.typing import RoleFunction, TitleGetter  # NOQA

builtin_extensions = (
    'sphinx.builders.applehelp',
    'sphinx.builders.changes',
    'sphinx.builders.epub3',
    'sphinx.builders.devhelp',
    'sphinx.builders.dummy',
    'sphinx.builders.gettext',
    'sphinx.builders.html',
    'sphinx.builders.htmlhelp',
    'sphinx.builders.latex',
    'sphinx.builders.linkcheck',
    'sphinx.builders.manpage',
    'sphinx.builders.qthelp',
    'sphinx.builders.texinfo',
    'sphinx.builders.text',
    'sphinx.builders.websupport',
    'sphinx.builders.xml',
    'sphinx.config',
    'sphinx.domains.c',
    'sphinx.domains.changeset',
    'sphinx.domains.cpp',
    'sphinx.domains.javascript',
    'sphinx.domains.math',
    'sphinx.domains.python',
    'sphinx.domains.rst',
    'sphinx.domains.std',
    'sphinx.directives',
    'sphinx.directives.code',
    'sphinx.directives.other',
    'sphinx.directives.patches',
    'sphinx.extension',
    'sphinx.io',
    'sphinx.parsers',
    'sphinx.registry',
    'sphinx.roles',
    'sphinx.transforms.post_transforms',
    'sphinx.transforms.post_transforms.code',
    'sphinx.transforms.post_transforms.images',
    'sphinx.transforms.post_transforms.compat',
    'sphinx.util.compat',
    # collectors should be loaded by specific order
    'sphinx.environment.collectors.dependencies',
    'sphinx.environment.collectors.asset',
    'sphinx.environment.collectors.metadata',
    'sphinx.environment.collectors.title',
    'sphinx.environment.collectors.toctree',
    'sphinx.environment.collectors.indexentries',
    # Strictly, alabaster theme is not a builtin extension,
    # but it is loaded automatically to use it as default theme.
    'alabaster',
)  # type: Tuple[unicode, ...]

ENV_PICKLE_FILENAME = 'environment.pickle'

logger = logging.getLogger(__name__)


class Sphinx(object):
    """The main application class and extensibility interface.

    :ivar srcdir: Directory containing source.
    :ivar confdir: Directory containing ``conf.py``.
    :ivar doctreedir: Directory for storing pickled doctrees.
    :ivar outdir: Directory for storing build documents.
    """

    def __init__(self, srcdir, confdir, outdir, doctreedir, buildername,
                 confoverrides=None, status=sys.stdout, warning=sys.stderr,
                 freshenv=False, warningiserror=False, tags=None, verbosity=0,
                 parallel=0, keep_going=False):
        # type: (unicode, unicode, unicode, unicode, unicode, Dict, IO, IO, bool, bool, List[unicode], int, int, bool) -> None  # NOQA
        self.phase = BuildPhase.INITIALIZATION
        self.verbosity = verbosity
        self.extensions = {}                    # type: Dict[unicode, Extension]
        self._setting_up_extension = ['?']      # type: List[unicode]
        self.builder = None                     # type: Builder
        self.env = None                         # type: BuildEnvironment
        self.registry = SphinxComponentRegistry()
        self.html_themes = {}                   # type: Dict[unicode, unicode]

        # validate provided directories
        self.srcdir = abspath(srcdir)           # type: unicode
        self.outdir = abspath(outdir)           # type: unicode
        self.doctreedir = abspath(doctreedir)   # type: unicode
        self.confdir = confdir
        if self.confdir:  # confdir is optional
            self.confdir = abspath(self.confdir)
            if not path.isfile(path.join(self.confdir, 'conf.py')):
                raise ApplicationError(__("config directory doesn't contain a "
                                          "conf.py file (%s)") % confdir)

        if not path.isdir(self.srcdir):
            raise ApplicationError(__('Cannot find source directory (%s)') %
                                   self.srcdir)

        if self.srcdir == self.outdir:
            raise ApplicationError(__('Source directory and destination '
                                      'directory cannot be identical'))

        self.parallel = parallel

        if status is None:
            self._status = cStringIO()      # type: IO
            self.quiet = True
        else:
            self._status = status
            self.quiet = False

        if warning is None:
            self._warning = cStringIO()     # type: IO
        else:
            self._warning = warning
        self._warncount = 0
        self.keep_going = warningiserror and keep_going
        if self.keep_going:
            self.warningiserror = False
        else:
            self.warningiserror = warningiserror
        logging.setup(self, self._status, self._warning)

        self.events = EventManager()

        # keep last few messages for traceback
        # This will be filled by sphinx.util.logging.LastMessagesWriter
        self.messagelog = deque(maxlen=10)  # type: deque

        # say hello to the world
        logger.info(bold(__('Running Sphinx v%s') % sphinx.__display_version__))

        # status code for command-line application
        self.statuscode = 0

        # read config
        self.tags = Tags(tags)
        if self.confdir is None:
            self.config = Config({}, confoverrides or {})
        else:
            self.config = Config.read(self.confdir, confoverrides or {}, self.tags)
            check_unicode(self.config)

        # initialize some limited config variables before initialize i18n and loading
        # extensions
        self.config.pre_init_values()

        # set up translation infrastructure
        self._init_i18n()

        # check the Sphinx version if requested
        if self.config.needs_sphinx and self.config.needs_sphinx > sphinx.__display_version__:
            raise VersionRequirementError(
                __('This project needs at least Sphinx v%s and therefore cannot '
                   'be built with this version.') % self.config.needs_sphinx)

        # set confdir to srcdir if -C given (!= no confdir); a few pieces
        # of code expect a confdir to be set
        if self.confdir is None:
            self.confdir = self.srcdir

        # load all built-in extension modules
        for extension in builtin_extensions:
            self.setup_extension(extension)

        # load all user-given extension modules
        for extension in self.config.extensions:
            self.setup_extension(extension)

        # preload builder module (before init config values)
        self.preload_builder(buildername)

        if not path.isdir(outdir):
            logger.info(__('making output directory...'))
            ensuredir(outdir)

        # the config file itself can be an extension
        if self.config.setup:
            self._setting_up_extension = ['conf.py']
            if callable(self.config.setup):
                self.config.setup(self)
            else:
                raise ConfigError(
                    __("'setup' as currently defined in conf.py isn't a Python callable. "
                       "Please modify its definition to make it a callable function. This is "
                       "needed for conf.py to behave as a Sphinx extension.")
                )

        # now that we know all config values, collect them from conf.py
        self.config.init_values()
        self.emit('config-inited', self.config)

        # check primary_domain if requested
        primary_domain = self.config.primary_domain
        if primary_domain and not self.registry.has_domain(primary_domain):
            logger.warning(__('primary_domain %r not found, ignored.'), primary_domain)

        # create the builder
        self.builder = self.create_builder(buildername)
        # set up the build environment
        self._init_env(freshenv)
        # set up the builder
        self._init_builder()

    def _init_i18n(self):
        # type: () -> None
        """Load translated strings from the configured localedirs if enabled in
        the configuration.
        """
        if self.config.language is not None:
            logger.info(bold(__('loading translations [%s]... ') % self.config.language),
                        nonl=True)
            user_locale_dirs = [
                path.join(self.srcdir, x) for x in self.config.locale_dirs]
            # compile mo files if sphinx.po file in user locale directories are updated
            for catinfo in find_catalog_source_files(
                    user_locale_dirs, self.config.language, domains=['sphinx'],
                    charset=self.config.source_encoding):
                catinfo.write_mo(self.config.language)
            locale_dirs = [None, path.join(package_dir, 'locale')] + user_locale_dirs  # type: ignore  # NOQA
        else:
            locale_dirs = []
        self.translator, has_translation = locale.init(locale_dirs, self.config.language)  # type: ignore  # NOQA
        if self.config.language is not None:
            if has_translation or self.config.language == 'en':
                # "en" never needs to be translated
                logger.info(__('done'))
            else:
                logger.info(__('not available for built-in messages'))

    def _init_env(self, freshenv):
        # type: (bool) -> None
        filename = path.join(self.doctreedir, ENV_PICKLE_FILENAME)
        if freshenv or not os.path.exists(filename):
            self.env = BuildEnvironment()
            self.env.setup(self)
            self.env.find_files(self.config, self.builder)
        else:
            try:
                logger.info(bold(__('loading pickled environment... ')), nonl=True)
                with open(filename, 'rb') as f:
                    self.env = pickle.load(f)
                    self.env.setup(self)
                logger.info(__('done'))
            except Exception as err:
                logger.info(__('failed: %s'), err)
                self._init_env(freshenv=True)

    def preload_builder(self, name):
        # type: (unicode) -> None
        self.registry.preload_builder(self, name)

    def create_builder(self, name):
        # type: (unicode) -> Builder
        if name is None:
            logger.info(__('No builder selected, using default: html'))
            name = 'html'

        return self.registry.create_builder(self, name)

    def _init_builder(self):
        # type: () -> None
        self.builder.set_environment(self.env)
        self.builder.init()
        self.emit('builder-inited')

    # ---- main "build" method -------------------------------------------------

    def build(self, force_all=False, filenames=None):
        # type: (bool, List[unicode]) -> None
        self.phase = BuildPhase.READING
        try:
            if force_all:
                self.builder.compile_all_catalogs()
                self.builder.build_all()
            elif filenames:
                self.builder.compile_specific_catalogs(filenames)
                self.builder.build_specific(filenames)
            else:
                self.builder.compile_update_catalogs()
                self.builder.build_update()

            if self._warncount and self.keep_going:
                self.statuscode = 1

            status = (self.statuscode == 0 and
                      __('succeeded') or __('finished with problems'))
            if self._warncount:
                logger.info(bold(__('build %s, %s warning.',
                                    'build %s, %s warnings.', self._warncount) %
                                 (status, self._warncount)))
            else:
                logger.info(bold(__('build %s.') % status))

            if self.statuscode == 0 and self.builder.epilog:
                logger.info('')
                logger.info(self.builder.epilog % {
                    'outdir': relpath(self.outdir),
                    'project': self.config.project
                })
        except Exception as err:
            # delete the saved env to force a fresh build next time
            envfile = path.join(self.doctreedir, ENV_PICKLE_FILENAME)
            if path.isfile(envfile):
                os.unlink(envfile)
            self.emit('build-finished', err)
            raise
        else:
            self.emit('build-finished', None)
        self.builder.cleanup()

    # ---- logging handling ----------------------------------------------------
    def warn(self, message, location=None, type=None, subtype=None):
        # type: (unicode, unicode, unicode, unicode) -> None
        """Emit a warning.

        If *location* is given, it should either be a tuple of (*docname*,
        *lineno*) or a string describing the location of the warning as well as
        possible.

        *type* and *subtype* are used to suppress warnings with
        :confval:`suppress_warnings`.

        .. deprecated:: 1.6
           Use :mod:`sphinx.util.logging` instead.
        """
        warnings.warn('app.warning() is now deprecated. Use sphinx.util.logging instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        logger.warning(message, type=type, subtype=subtype, location=location)

    def info(self, message='', nonl=False):
        # type: (unicode, bool) -> None
        """Emit an informational message.

        If *nonl* is true, don't emit a newline at the end (which implies that
        more info output will follow soon.)

        .. deprecated:: 1.6
           Use :mod:`sphinx.util.logging` instead.
        """
        warnings.warn('app.info() is now deprecated. Use sphinx.util.logging instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        logger.info(message, nonl=nonl)

    def verbose(self, message, *args, **kwargs):
        # type: (unicode, Any, Any) -> None
        """Emit a verbose informational message.

        .. deprecated:: 1.6
           Use :mod:`sphinx.util.logging` instead.
        """
        warnings.warn('app.verbose() is now deprecated. Use sphinx.util.logging instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        logger.verbose(message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        # type: (unicode, Any, Any) -> None
        """Emit a debug-level informational message.

        .. deprecated:: 1.6
           Use :mod:`sphinx.util.logging` instead.
        """
        warnings.warn('app.debug() is now deprecated. Use sphinx.util.logging instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        logger.debug(message, *args, **kwargs)

    def debug2(self, message, *args, **kwargs):
        # type: (unicode, Any, Any) -> None
        """Emit a lowlevel debug-level informational message.

        .. deprecated:: 1.6
           Use :mod:`sphinx.util.logging` instead.
        """
        warnings.warn('app.debug2() is now deprecated. Use debug() instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        logger.debug(message, *args, **kwargs)

    # ---- general extensibility interface -------------------------------------

    def setup_extension(self, extname):
        # type: (unicode) -> None
        """Import and setup a Sphinx extension module.

        Load the extension given by the module *name*.  Use this if your
        extension needs the features provided by another extension.  No-op if
        called twice.
        """
        logger.debug('[app] setting up extension: %r', extname)
        self.registry.load_extension(self, extname)

    def require_sphinx(self, version):
        # type: (unicode) -> None
        """Check the Sphinx version if requested.

        Compare *version* (which must be a ``major.minor`` version string, e.g.
        ``'1.1'``) with the version of the running Sphinx, and abort the build
        when it is too old.

        .. versionadded:: 1.0
        """
        if version > sphinx.__display_version__[:3]:
            raise VersionRequirementError(version)

    def import_object(self, objname, source=None):
        # type: (str, unicode) -> Any
        """Import an object from a ``module.name`` string.

        .. deprecated:: 1.8
           Use ``sphinx.util.import_object()`` instead.
        """
        warnings.warn('app.import_object() is deprecated. '
                      'Use sphinx.util.add_object_type() instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return import_object(objname, source=None)

    # event interface
    def connect(self, event, callback):
        # type: (unicode, Callable) -> int
        """Register *callback* to be called when *event* is emitted.

        For details on available core events and the arguments of callback
        functions, please see :ref:`events`.

        The method returns a "listener ID" that can be used as an argument to
        :meth:`disconnect`.
        """
        listener_id = self.events.connect(event, callback)
        logger.debug('[app] connecting event %r: %r [id=%s]', event, callback, listener_id)
        return listener_id

    def disconnect(self, listener_id):
        # type: (int) -> None
        """Unregister callback by *listener_id*."""
        logger.debug('[app] disconnecting event: [id=%s]', listener_id)
        self.events.disconnect(listener_id)

    def emit(self, event, *args):
        # type: (unicode, Any) -> List
        """Emit *event* and pass *arguments* to the callback functions.

        Return the return values of all callbacks as a list.  Do not emit core
        Sphinx events in extensions!
        """
        try:
            logger.debug('[app] emitting event: %r%s', event, repr(args)[:100])
        except Exception:
            # not every object likes to be repr()'d (think
            # random stuff coming via autodoc)
            pass
        return self.events.emit(event, self, *args)

    def emit_firstresult(self, event, *args):
        # type: (unicode, Any) -> Any
        """Emit *event* and pass *arguments* to the callback functions.

        Return the result of the first callback that doesn't return ``None``.

        .. versionadded:: 0.5
        """
        return self.events.emit_firstresult(event, self, *args)

    # registering addon parts

    def add_builder(self, builder, override=False):
        # type: (Type[Builder], bool) -> None
        """Register a new builder.

        *builder* must be a class that inherits from
        :class:`~sphinx.builders.Builder`.

        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_builder(builder, override=override)

    # TODO(stephenfin): Describe 'types' parameter
    def add_config_value(self, name, default, rebuild, types=()):
        # type: (unicode, Any, Union[bool, unicode], Any) -> None
        """Register a configuration value.

        This is necessary for Sphinx to recognize new values and set default
        values accordingly.  The *name* should be prefixed with the extension
        name, to avoid clashes.  The *default* value can be any Python object.
        The string value *rebuild* must be one of those values:

        * ``'env'`` if a change in the setting only takes effect when a
          document is parsed -- this means that the whole environment must be
          rebuilt.
        * ``'html'`` if a change in the setting needs a full rebuild of HTML
          documents.
        * ``''`` if a change in the setting will not need any special rebuild.

        .. versionchanged:: 0.6
           Changed *rebuild* from a simple boolean (equivalent to ``''`` or
           ``'env'``) to a string.  However, booleans are still accepted and
           converted internally.

        .. versionchanged:: 0.4
           If the *default* value is a callable, it will be called with the
           config object as its argument in order to get the default value.
           This can be used to implement config values whose default depends on
           other values.
        """
        logger.debug('[app] adding config value: %r',
                     (name, default, rebuild) + ((types,) if types else ()))  # type: ignore
        if rebuild in (False, True):
            rebuild = rebuild and 'env' or ''
        self.config.add(name, default, rebuild, types)

    def add_event(self, name):
        # type: (unicode) -> None
        """Register an event called *name*.

        This is needed to be able to emit it.
        """
        logger.debug('[app] adding event: %r', name)
        self.events.add(name)

    def set_translator(self, name, translator_class, override=False):
        # type: (unicode, Type[nodes.NodeVisitor], bool) -> None
        """Register or override a Docutils translator class.

        This is used to register a custom output translator or to replace a
        builtin translator.  This allows extensions to use custom translator
        and define custom nodes for the translator (see :meth:`add_node`).

        .. versionadded:: 1.3
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_translator(name, translator_class, override=override)

    def add_node(self, node, override=False, **kwds):
        # type: (nodes.Node, bool, Any) -> None
        """Register a Docutils node class.

        This is necessary for Docutils internals.  It may also be used in the
        future to validate nodes in the parsed documents.

        Node visitor functions for the Sphinx HTML, LaTeX, text and manpage
        writers can be given as keyword arguments: the keyword should be one or
        more of ``'html'``, ``'latex'``, ``'text'``, ``'man'``, ``'texinfo'``
        or any other supported translators, the value a 2-tuple of ``(visit,
        depart)`` methods.  ``depart`` can be ``None`` if the ``visit``
        function raises :exc:`docutils.nodes.SkipNode`.  Example:

        .. code-block:: python

           class math(docutils.nodes.Element): pass

           def visit_math_html(self, node):
               self.body.append(self.starttag(node, 'math'))
           def depart_math_html(self, node):
               self.body.append('</math>')

           app.add_node(math, html=(visit_math_html, depart_math_html))

        Obviously, translators for which you don't specify visitor methods will
        choke on the node when encountered in a document to translate.

        .. versionchanged:: 0.5
           Added the support for keyword arguments giving visit functions.
        """
        logger.debug('[app] adding node: %r', (node, kwds))
        if not override and docutils.is_node_registered(node):
            logger.warning(__('while setting up extension %s: node class %r is '
                              'already registered, its visitors will be overridden'),
                           self._setting_up_extension[-1], node.__name__,
                           type='app', subtype='add_node')
        docutils.register_node(node)
        self.registry.add_translation_handlers(node, **kwds)

    def add_enumerable_node(self, node, figtype, title_getter=None, override=False, **kwds):
        # type: (nodes.Node, unicode, TitleGetter, bool, Any) -> None
        """Register a Docutils node class as a numfig target.

        Sphinx numbers the node automatically. And then the users can refer it
        using :rst:role:`numref`.

        *figtype* is a type of enumerable nodes.  Each figtypes have individual
        numbering sequences.  As a system figtypes, ``figure``, ``table`` and
        ``code-block`` are defined.  It is able to add custom nodes to these
        default figtypes.  It is also able to define new custom figtype if new
        figtype is given.

        *title_getter* is a getter function to obtain the title of node.  It
        takes an instance of the enumerable node, and it must return its title
        as string.  The title is used to the default title of references for
        :rst:role:`ref`.  By default, Sphinx searches
        ``docutils.nodes.caption`` or ``docutils.nodes.title`` from the node as
        a title.

        Other keyword arguments are used for node visitor functions. See the
        :meth:`.Sphinx.add_node` for details.

        .. versionadded:: 1.4
        """
        self.registry.add_enumerable_node(node, figtype, title_getter, override=override)
        self.add_node(node, override=override, **kwds)

    @property
    def enumerable_nodes(self):
        # type: () -> Dict[nodes.Node, Tuple[unicode, TitleGetter]]
        warnings.warn('app.enumerable_nodes() is deprecated. '
                      'Use app.get_domain("std").enumerable_nodes instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return self.registry.enumerable_nodes

    def add_directive(self, name, obj, content=None, arguments=None, override=False, **options):  # NOQA
        # type: (unicode, Any, bool, Tuple[int, int, bool], bool, Any) -> None
        """Register a Docutils directive.

        *name* must be the prospective directive name.  There are two possible
        ways to write a directive:

        - In the docutils 0.4 style, *obj* is the directive function.
          *content*, *arguments* and *options* are set as attributes on the
          function and determine whether the directive has content, arguments
          and options, respectively.  **This style is deprecated.**

        - In the docutils 0.5 style, *obj* is the directive class.
          It must already have attributes named *has_content*,
          *required_arguments*, *optional_arguments*,
          *final_argument_whitespace* and *option_spec* that correspond to the
          options for the function way.  See `the Docutils docs
          <http://docutils.sourceforge.net/docs/howto/rst-directives.html>`_
          for details.

        The directive class must inherit from the class
        ``docutils.parsers.rst.Directive``.

        For example, the (already existing) :rst:dir:`literalinclude` directive
        would be added like this:

        .. code-block:: python

           from docutils.parsers.rst import Directive, directives

           class LiteralIncludeDirective(Directive):
               has_content = True
               required_arguments = 1
               optional_arguments = 0
               final_argument_whitespace = True
               option_spec = {
                   'class': directives.class_option,
                   'name': directives.unchanged,
               }

               def run(self):
                   ...

           add_directive('literalinclude', LiteralIncludeDirective)

        .. versionchanged:: 0.6
           Docutils 0.5-style directive classes are now supported.
        .. deprecated:: 1.8
           Docutils 0.4-style (function based) directives support is deprecated.
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        logger.debug('[app] adding directive: %r',
                     (name, obj, content, arguments, options))
        if name in directives._directives and not override:
            logger.warning(__('while setting up extension %s: directive %r is '
                              'already registered, it will be overridden'),
                           self._setting_up_extension[-1], name,
                           type='app', subtype='add_directive')

        if not isclass(obj) or not issubclass(obj, Directive):
            directive = directive_helper(obj, content, arguments, **options)
            directives.register_directive(name, directive)
        else:
            directives.register_directive(name, obj)

    def add_role(self, name, role, override=False):
        # type: (unicode, Any, bool) -> None
        """Register a Docutils role.

        *name* must be the role name that occurs in the source, *role* the role
        function. Refer to the `Docutils documentation
        <http://docutils.sourceforge.net/docs/howto/rst-roles.html>`_ for
        more information.

        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        logger.debug('[app] adding role: %r', (name, role))
        if name in roles._roles and not override:
            logger.warning(__('while setting up extension %s: role %r is '
                              'already registered, it will be overridden'),
                           self._setting_up_extension[-1], name,
                           type='app', subtype='add_role')
        roles.register_local_role(name, role)

    def add_generic_role(self, name, nodeclass, override=False):
        # type: (unicode, Any, bool) -> None
        """Register a generic Docutils role.

        Register a Docutils role that does nothing but wrap its contents in the
        node given by *nodeclass*.

        .. versionadded:: 0.6
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        # Don't use ``roles.register_generic_role`` because it uses
        # ``register_canonical_role``.
        logger.debug('[app] adding generic role: %r', (name, nodeclass))
        if name in roles._roles and not override:
            logger.warning(__('while setting up extension %s: role %r is '
                              'already registered, it will be overridden'),
                           self._setting_up_extension[-1], name,
                           type='app', subtype='add_generic_role')
        role = roles.GenericRole(name, nodeclass)
        roles.register_local_role(name, role)

    def add_domain(self, domain, override=False):
        # type: (Type[Domain], bool) -> None
        """Register a domain.

        Make the given *domain* (which must be a class; more precisely, a
        subclass of :class:`~sphinx.domains.Domain`) known to Sphinx.

        .. versionadded:: 1.0
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_domain(domain, override=override)

    def override_domain(self, domain):
        # type: (Type[Domain]) -> None
        """Override a registered domain.

        Make the given *domain* class known to Sphinx, assuming that there is
        already a domain with its ``.name``.  The new domain must be a subclass
        of the existing one.

        .. versionadded:: 1.0
        .. deprecated:: 1.8
           Integrated to :meth:`add_domain`.
        """
        warnings.warn('app.override_domain() is deprecated. '
                      'Use app.add_domain() with override option instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        self.registry.add_domain(domain, override=True)

    def add_directive_to_domain(self, domain, name, obj, has_content=None, argument_spec=None,
                                override=False, **option_spec):
        # type: (unicode, unicode, Any, bool, Any, bool, Any) -> None
        """Register a Docutils directive in a domain.

        Like :meth:`add_directive`, but the directive is added to the domain
        named *domain*.

        .. versionadded:: 1.0
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_directive_to_domain(domain, name, obj,
                                              has_content, argument_spec, override=override,
                                              **option_spec)

    def add_role_to_domain(self, domain, name, role, override=False):
        # type: (unicode, unicode, Union[RoleFunction, XRefRole], bool) -> None
        """Register a Docutils role in a domain.

        Like :meth:`add_role`, but the role is added to the domain named
        *domain*.

        .. versionadded:: 1.0
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_role_to_domain(domain, name, role, override=override)

    def add_index_to_domain(self, domain, index, override=False):
        # type: (unicode, Type[Index], bool) -> None
        """Register a custom index for a domain.

        Add a custom *index* class to the domain named *domain*.  *index* must
        be a subclass of :class:`~sphinx.domains.Index`.

        .. versionadded:: 1.0
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_index_to_domain(domain, index)

    def add_object_type(self, directivename, rolename, indextemplate='',
                        parse_node=None, ref_nodeclass=None, objname='',
                        doc_field_types=[], override=False):
        # type: (unicode, unicode, unicode, Callable, nodes.Node, unicode, List, bool) -> None
        """Register a new object type.

        This method is a very convenient way to add a new :term:`object` type
        that can be cross-referenced.  It will do this:

        - Create a new directive (called *directivename*) for documenting an
          object.  It will automatically add index entries if *indextemplate*
          is nonempty; if given, it must contain exactly one instance of
          ``%s``.  See the example below for how the template will be
          interpreted.
        - Create a new role (called *rolename*) to cross-reference to these
          object descriptions.
        - If you provide *parse_node*, it must be a function that takes a
          string and a docutils node, and it must populate the node with
          children parsed from the string.  It must then return the name of the
          item to be used in cross-referencing and index entries.  See the
          :file:`conf.py` file in the source for this documentation for an
          example.
        - The *objname* (if not given, will default to *directivename*) names
          the type of object.  It is used when listing objects, e.g. in search
          results.

        For example, if you have this call in a custom Sphinx extension::

           app.add_object_type('directive', 'dir', 'pair: %s; directive')

        you can use this markup in your documents::

           .. rst:directive:: function

              Document a function.

           <...>

           See also the :rst:dir:`function` directive.

        For the directive, an index entry will be generated as if you had prepended ::

           .. index:: pair: function; directive

        The reference node will be of class ``literal`` (so it will be rendered
        in a proportional font, as appropriate for code) unless you give the
        *ref_nodeclass* argument, which must be a docutils node class.  Most
        useful are ``docutils.nodes.emphasis`` or ``docutils.nodes.strong`` --
        you can also use ``docutils.nodes.generated`` if you want no further
        text decoration.  If the text should be treated as literal (e.g. no
        smart quote replacement), but not have typewriter styling, use
        ``sphinx.addnodes.literal_emphasis`` or
        ``sphinx.addnodes.literal_strong``.

        For the role content, you have the same syntactical possibilities as
        for standard Sphinx roles (see :ref:`xref-syntax`).

        This method is also available under the deprecated alias
        :meth:`add_description_unit`.

        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_object_type(directivename, rolename, indextemplate, parse_node,
                                      ref_nodeclass, objname, doc_field_types,
                                      override=override)

    def add_description_unit(self, directivename, rolename, indextemplate='',
                             parse_node=None, ref_nodeclass=None, objname='',
                             doc_field_types=[]):
        # type: (unicode, unicode, unicode, Callable, nodes.Node, unicode, List) -> None
        """Deprecated alias for :meth:`add_object_type`.

        .. deprecated:: 1.6
           Use :meth:`add_object_type` instead.
        """
        warnings.warn('app.add_description_unit() is now deprecated. '
                      'Use app.add_object_type() instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        self.add_object_type(directivename, rolename, indextemplate, parse_node,
                             ref_nodeclass, objname, doc_field_types)

    def add_crossref_type(self, directivename, rolename, indextemplate='',
                          ref_nodeclass=None, objname='', override=False):
        # type: (unicode, unicode, unicode, nodes.Node, unicode, bool) -> None
        """Register a new crossref object type.

        This method is very similar to :meth:`add_object_type` except that the
        directive it generates must be empty, and will produce no output.

        That means that you can add semantic targets to your sources, and refer
        to them using custom roles instead of generic ones (like
        :rst:role:`ref`).  Example call::

           app.add_crossref_type('topic', 'topic', 'single: %s',
                                 docutils.nodes.emphasis)

        Example usage::

           .. topic:: application API

           The application API
           -------------------

           Some random text here.

           See also :topic:`this section <application API>`.

        (Of course, the element following the ``topic`` directive needn't be a
        section.)

        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_crossref_type(directivename, rolename,
                                        indextemplate, ref_nodeclass, objname,
                                        override=override)

    def add_transform(self, transform):
        # type: (Type[Transform]) -> None
        """Register a Docutils transform to be applied after parsing.

        Add the standard docutils :class:`Transform` subclass *transform* to
        the list of transforms that are applied after Sphinx parses a reST
        document.

        .. list-table:: priority range categories for Sphinx transforms
           :widths: 20,80

           * - Priority
             - Main purpose in Sphinx
           * - 0-99
             - Fix invalid nodes by docutils. Translate a doctree.
           * - 100-299
             - Preparation
           * - 300-399
             - early
           * - 400-699
             - main
           * - 700-799
             - Post processing. Deadline to modify text and referencing.
           * - 800-899
             - Collect referencing and referenced nodes. Domain processing.
           * - 900-999
             - Finalize and clean up.

        refs: `Transform Priority Range Categories`__

        __ http://docutils.sourceforge.net/docs/ref/transforms.html#transform-priority-range-categories
        """  # NOQA
        self.registry.add_transform(transform)

    def add_post_transform(self, transform):
        # type: (Type[Transform]) -> None
        """Register a Docutils transform to be applied before writing.

        Add the standard docutils :class:`Transform` subclass *transform* to
        the list of transforms that are applied before Sphinx writes a
        document.
        """
        self.registry.add_post_transform(transform)

    def add_javascript(self, filename, **kwargs):
        # type: (unicode, **unicode) -> None
        """An alias of :meth:`add_js_file`."""
        warnings.warn('The app.add_javascript() is deprecated. '
                      'Please use app.add_js_file() instead.',
                      RemovedInSphinx40Warning, stacklevel=2)
        self.add_js_file(filename, **kwargs)

    def add_js_file(self, filename, **kwargs):
        # type: (unicode, **unicode) -> None
        """Register a JavaScript file to include in the HTML output.

        Add *filename* to the list of JavaScript files that the default HTML
        template will include.  The filename must be relative to the HTML
        static path , or a full URI with scheme.  The keyword arguments are
        also accepted for attributes of ``<script>`` tag.

        Example::

            app.add_js_file('example.js')
            # => <script src="_static/example.js"></script>

            app.add_js_file('example.js', async="async")
            # => <script src="_static/example.js" async="async"></script>

        .. versionadded:: 0.5

        .. versionchanged:: 1.8
           Renamed from ``app.add_javascript()``.
           And it allows keyword arguments as attributes of script tag.
        """
        self.registry.add_js_file(filename, **kwargs)
        if hasattr(self.builder, 'add_js_file'):
            self.builder.add_js_file(filename, **kwargs)  # type: ignore

    def add_css_file(self, filename, **kwargs):
        # type: (unicode, **unicode) -> None
        """Register a stylesheet to include in the HTML output.

        Add *filename* to the list of CSS files that the default HTML template
        will include.  The filename must be relative to the HTML static path,
        or a full URI with scheme.  The keyword arguments are also accepted for
        attributes of ``<link>`` tag.

        Example::

            app.add_css_file('custom.css')
            # => <link rel="stylesheet" href="_static/custom.css" type="text/css" />

            app.add_css_file('print.css', media='print')
            # => <link rel="stylesheet" href="_static/print.css"
            #          type="text/css" media="print" />

            app.add_css_file('fancy.css', rel='alternate stylesheet', title='fancy')
            # => <link rel="alternate stylesheet" href="_static/fancy.css"
            #          type="text/css" title="fancy" />

        .. versionadded:: 1.0

        .. versionchanged:: 1.6
           Optional ``alternate`` and/or ``title`` attributes can be supplied
           with the *alternate* (of boolean type) and *title* (a string)
           arguments. The default is no title and *alternate* = ``False``. For
           more information, refer to the `documentation
           <https://mdn.io/Web/CSS/Alternative_style_sheets>`__.

        .. versionchanged:: 1.8
           Renamed from ``app.add_stylesheet()``.
           And it allows keyword arguments as attributes of link tag.
        """
        logger.debug('[app] adding stylesheet: %r', filename)
        self.registry.add_css_files(filename, **kwargs)
        if hasattr(self.builder, 'add_css_file'):
            self.builder.add_css_file(filename, **kwargs)  # type: ignore

    def add_stylesheet(self, filename, alternate=False, title=None):
        # type: (unicode, bool, unicode) -> None
        """An alias of :meth:`add_css_file`."""
        warnings.warn('The app.add_stylesheet() is deprecated. '
                      'Please use app.add_css_file() instead.',
                      RemovedInSphinx40Warning, stacklevel=2)

        attributes = {}  # type: Dict[unicode, unicode]
        if alternate:
            attributes['rel'] = 'alternate stylesheet'
        else:
            attributes['rel'] = 'stylesheet'

        if title:
            attributes['title'] = title

        self.add_css_file(filename, **attributes)

    def add_latex_package(self, packagename, options=None):
        # type: (unicode, unicode) -> None
        r"""Register a package to include in the LaTeX source code.

        Add *packagename* to the list of packages that LaTeX source code will
        include.  If you provide *options*, it will be taken to `\usepackage`
        declaration.

        .. code-block:: python

           app.add_latex_package('mypackage')
           # => \usepackage{mypackage}
           app.add_latex_package('mypackage', 'foo,bar')
           # => \usepackage[foo,bar]{mypackage}

        .. versionadded:: 1.3
        """
        self.registry.add_latex_package(packagename, options)

    def add_lexer(self, alias, lexer):
        # type: (unicode, Any) -> None
        """Register a new lexer for source code.

        Use *lexer*, which must be an instance of a Pygments lexer class, to
        highlight code blocks with the given language *alias*.

        .. versionadded:: 0.6
        """
        logger.debug('[app] adding lexer: %r', (alias, lexer))
        from sphinx.highlighting import lexers
        if lexers is None:
            return
        lexers[alias] = lexer

    def add_autodocumenter(self, cls):
        # type: (Any) -> None
        """Register a new documenter class for the autodoc extension.

        Add *cls* as a new documenter class for the :mod:`sphinx.ext.autodoc`
        extension.  It must be a subclass of
        :class:`sphinx.ext.autodoc.Documenter`.  This allows to auto-document
        new types of objects.  See the source of the autodoc module for
        examples on how to subclass :class:`Documenter`.

        .. todo:: Add real docs for Documenter and subclassing

        .. versionadded:: 0.6
        """
        logger.debug('[app] adding autodocumenter: %r', cls)
        from sphinx.ext.autodoc.directive import AutodocDirective
        self.registry.add_documenter(cls.objtype, cls)
        self.add_directive('auto' + cls.objtype, AutodocDirective)

    def add_autodoc_attrgetter(self, typ, getter):
        # type: (Type, Callable[[Any, unicode, Any], Any]) -> None
        """Register a new ``getattr``-like function for the autodoc extension.

        Add *getter*, which must be a function with an interface compatible to
        the :func:`getattr` builtin, as the autodoc attribute getter for
        objects that are instances of *typ*.  All cases where autodoc needs to
        get an attribute of a type are then handled by this function instead of
        :func:`getattr`.

        .. versionadded:: 0.6
        """
        logger.debug('[app] adding autodoc attrgetter: %r', (typ, getter))
        self.registry.add_autodoc_attrgetter(typ, getter)

    def add_search_language(self, cls):
        # type: (Any) -> None
        """Register a new language for the HTML search index.

        Add *cls*, which must be a subclass of
        :class:`sphinx.search.SearchLanguage`, as a support language for
        building the HTML full-text search index.  The class must have a *lang*
        attribute that indicates the language it should be used for.  See
        :confval:`html_search_language`.

        .. versionadded:: 1.1
        """
        logger.debug('[app] adding search language: %r', cls)
        from sphinx.search import languages, SearchLanguage
        assert issubclass(cls, SearchLanguage)
        languages[cls.lang] = cls

    def add_source_suffix(self, suffix, filetype, override=False):
        # type: (unicode, unicode, bool) -> None
        """Register a suffix of source files.

        Same as :confval:`source_suffix`.  The users can override this
        using the setting.

        .. versionadded:: 1.8
        """
        self.registry.add_source_suffix(suffix, filetype, override=override)

    def add_source_parser(self, *args, **kwargs):
        # type: (Any, Any) -> None
        """Register a parser class.

        .. versionadded:: 1.4
        .. versionchanged:: 1.8
           *suffix* argument is deprecated.  It only accepts *parser* argument.
           Use :meth:`add_source_suffix` API to register suffix instead.
        .. versionchanged:: 1.8
           Add *override* keyword.
        """
        self.registry.add_source_parser(*args, **kwargs)

    def add_env_collector(self, collector):
        # type: (Type[EnvironmentCollector]) -> None
        """Register an environment collector class.

        Refer to :ref:`collector-api`.

        .. versionadded:: 1.6
        """
        logger.debug('[app] adding environment collector: %r', collector)
        collector().enable(self)

    def add_html_theme(self, name, theme_path):
        # type: (unicode, unicode) -> None
        """Register a HTML Theme.

        The *name* is a name of theme, and *path* is a full path to the theme
        (refs: :ref:`distribute-your-theme`).

        .. versionadded:: 1.6
        """
        logger.debug('[app] adding HTML theme: %r, %r', name, theme_path)
        self.html_themes[name] = theme_path

    def add_html_math_renderer(self, name, inline_renderers=None, block_renderers=None):
        # type: (unicode, Tuple[Callable, Callable], Tuple[Callable, Callable]) -> None
        """Register a math renderer for HTML.

        The *name* is a name of math renderer.  Both *inline_renderers* and
        *block_renderers* are used as visitor functions for the HTML writer:
        the former for inline math node (``nodes.math``), the latter for
        block math node (``nodes.math_block``).  Regarding visitor functions,
        see :meth:`add_node` for details.

        .. versionadded:: 1.8

        """
        self.registry.add_html_math_renderer(name, inline_renderers, block_renderers)

    def add_message_catalog(self, catalog, locale_dir):
        # type: (unicode, unicode) -> None
        """Register a message catalog.

        The *catalog* is a name of catalog, and *locale_dir* is a base path
        of message catalog.  For more details, see
        :func:`sphinx.locale.get_translation()`.

        .. versionadded:: 1.8
        """
        locale.init([locale_dir], self.config.language, catalog)
        locale.init_console(locale_dir, catalog)

    # ---- other methods -------------------------------------------------
    def is_parallel_allowed(self, typ):
        # type: (unicode) -> bool
        """Check parallel processing is allowed or not.

        ``typ`` is a type of processing; ``'read'`` or ``'write'``.
        """
        if typ == 'read':
            attrname = 'parallel_read_safe'
            message = __("the %s extension does not declare if it is safe "
                         "for parallel reading, assuming it isn't - please "
                         "ask the extension author to check and make it "
                         "explicit")
        elif typ == 'write':
            attrname = 'parallel_write_safe'
            message = __("the %s extension does not declare if it is safe "
                         "for parallel writing, assuming it isn't - please "
                         "ask the extension author to check and make it "
                         "explicit")
        else:
            raise ValueError('parallel type %s is not supported' % typ)

        for ext in itervalues(self.extensions):
            allowed = getattr(ext, attrname, None)
            if allowed is None:
                logger.warning(message, ext.name)
                logger.warning(__('doing serial %s'), typ)
                return False
            elif not allowed:
                return False

        return True


class TemplateBridge(object):
    """
    This class defines the interface for a "template bridge", that is, a class
    that renders templates given a template name and a context.
    """

    def init(self, builder, theme=None, dirs=None):
        # type: (Builder, Theme, List[unicode]) -> None
        """Called by the builder to initialize the template system.

        *builder* is the builder object; you'll probably want to look at the
        value of ``builder.config.templates_path``.

        *theme* is a :class:`sphinx.theming.Theme` object or None; in the latter
        case, *dirs* can be list of fixed directories to look for templates.
        """
        raise NotImplementedError('must be implemented in subclasses')

    def newest_template_mtime(self):
        # type: () -> float
        """Called by the builder to determine if output files are outdated
        because of template changes.  Return the mtime of the newest template
        file that was changed.  The default implementation returns ``0``.
        """
        return 0

    def render(self, template, context):
        # type: (unicode, Dict) -> None
        """Called by the builder to render a template given as a filename with
        a specified context (a Python dictionary).
        """
        raise NotImplementedError('must be implemented in subclasses')

    def render_string(self, template, context):
        # type: (unicode, Dict) -> unicode
        """Called by the builder to render a template given as a string with a
        specified context (a Python dictionary).
        """
        raise NotImplementedError('must be implemented in subclasses')
