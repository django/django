"""Build configuration file handling."""

from __future__ import annotations

import time
import traceback
import types
from os import getenv, path
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from sphinx.errors import ConfigError, ExtensionError
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.osutil import fs_encoding
from sphinx.util.typing import NoneType

try:
    from contextlib import chdir  # type: ignore[attr-defined]
except ImportError:
    from sphinx.util.osutil import _chdir as chdir

if TYPE_CHECKING:
    import os
    from collections.abc import Generator, Iterator, Sequence

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.tags import Tags

logger = logging.getLogger(__name__)

CONFIG_FILENAME = 'conf.py'
UNSERIALIZABLE_TYPES = (type, types.ModuleType, types.FunctionType)


class ConfigValue(NamedTuple):
    name: str
    value: Any
    rebuild: bool | str


def is_serializable(obj: Any) -> bool:
    """Check if object is serializable or not."""
    if isinstance(obj, UNSERIALIZABLE_TYPES):
        return False
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if not is_serializable(key) or not is_serializable(value):
                return False
    elif isinstance(obj, (list, tuple, set)):
        return all(is_serializable(i) for i in obj)

    return True


class ENUM:
    """Represents the candidates which a config value should be one of.

    Example:
        app.add_config_value('latex_show_urls', 'no', None, ENUM('no', 'footnote', 'inline'))
    """
    def __init__(self, *candidates: str | bool | None) -> None:
        self.candidates = candidates

    def match(self, value: str | list | tuple) -> bool:
        if isinstance(value, (list, tuple)):
            return all(item in self.candidates for item in value)
        else:
            return value in self.candidates


class Config:
    r"""Configuration file abstraction.

    The config object makes the values of all config values available as
    attributes.

    It is exposed via the :py:class:`~sphinx.application.Sphinx`\ ``.config``
    and :py:class:`sphinx.environment.BuildEnvironment`\ ``.config`` attributes.
    For example, to get the value of :confval:`language`, use either
    ``app.config.language`` or ``env.config.language``.
    """

    # the values are: (default, what needs to be rebuilt if changed)

    # If you add a value here, don't forget to include it in the
    # quickstart.py file template as well as in the docs!

    config_values: dict[str, tuple] = {
        # general options
        'project': ('Python', 'env', []),
        'author': ('unknown', 'env', []),
        'project_copyright': ('', 'html', [str, tuple, list]),
        'copyright': (lambda c: c.project_copyright, 'html', [str, tuple, list]),
        'version': ('', 'env', []),
        'release': ('', 'env', []),
        'today': ('', 'env', []),
        # the real default is locale-dependent
        'today_fmt': (None, 'env', [str]),

        'language': ('en', 'env', [str]),
        'locale_dirs': (['locales'], 'env', []),
        'figure_language_filename': ('{root}.{language}{ext}', 'env', [str]),
        'gettext_allow_fuzzy_translations': (False, 'gettext', []),
        'translation_progress_classes': (False, 'env',
                                         ENUM(True, False, 'translated', 'untranslated')),

        'master_doc': ('index', 'env', []),
        'root_doc': (lambda config: config.master_doc, 'env', []),
        'source_suffix': ({'.rst': 'restructuredtext'}, 'env', Any),
        'source_encoding': ('utf-8-sig', 'env', []),
        'exclude_patterns': ([], 'env', [str]),
        'include_patterns': (["**"], 'env', [str]),
        'default_role': (None, 'env', [str]),
        'add_function_parentheses': (True, 'env', []),
        'add_module_names': (True, 'env', []),
        'toc_object_entries': (True, 'env', [bool]),
        'toc_object_entries_show_parents': ('domain', 'env',
                                            ENUM('domain', 'all', 'hide')),
        'trim_footnote_reference_space': (False, 'env', []),
        'show_authors': (False, 'env', []),
        'pygments_style': (None, 'html', [str]),
        'highlight_language': ('default', 'env', []),
        'highlight_options': ({}, 'env', []),
        'templates_path': ([], 'html', []),
        'template_bridge': (None, 'html', [str]),
        'keep_warnings': (False, 'env', []),
        'suppress_warnings': ([], 'env', []),
        'modindex_common_prefix': ([], 'html', []),
        'rst_epilog': (None, 'env', [str]),
        'rst_prolog': (None, 'env', [str]),
        'trim_doctest_flags': (True, 'env', []),
        'primary_domain': ('py', 'env', [NoneType]),
        'needs_sphinx': (None, None, [str]),
        'needs_extensions': ({}, None, []),
        'manpages_url': (None, 'env', []),
        'nitpicky': (False, None, []),
        'nitpick_ignore': ([], None, [set, list, tuple]),
        'nitpick_ignore_regex': ([], None, [set, list, tuple]),
        'numfig': (False, 'env', []),
        'numfig_secnum_depth': (1, 'env', []),
        'numfig_format': ({}, 'env', []),  # will be initialized in init_numfig_format()
        'maximum_signature_line_length': (None, 'env', {int, None}),
        'math_number_all': (False, 'env', []),
        'math_eqref_format': (None, 'env', [str]),
        'math_numfig': (True, 'env', []),
        'tls_verify': (True, 'env', []),
        'tls_cacerts': (None, 'env', []),
        'user_agent': (None, 'env', [str]),
        'smartquotes': (True, 'env', []),
        'smartquotes_action': ('qDe', 'env', []),
        'smartquotes_excludes': ({'languages': ['ja'],
                                  'builders': ['man', 'text']},
                                 'env', []),
        'option_emphasise_placeholders': (False, 'env', []),
    }

    def __init__(self, config: dict[str, Any] | None = None,
                 overrides: dict[str, Any] | None = None) -> None:
        config = config or {}
        self.overrides = dict(overrides) if overrides is not None else {}
        self.values = Config.config_values.copy()
        self._raw_config = config
        self.setup: Callable | None = config.get('setup', None)

        if 'extensions' in self.overrides:
            if isinstance(self.overrides['extensions'], str):
                config['extensions'] = self.overrides.pop('extensions').split(',')
            else:
                config['extensions'] = self.overrides.pop('extensions')
        self.extensions: list[str] = config.get('extensions', [])

    @classmethod
    def read(cls, confdir: str | os.PathLike[str], overrides: dict | None = None,
             tags: Tags | None = None) -> Config:
        """Create a Config object from configuration file."""
        filename = path.join(confdir, CONFIG_FILENAME)
        if not path.isfile(filename):
            raise ConfigError(__("config directory doesn't contain a conf.py file (%s)") %
                              confdir)
        namespace = eval_config_file(filename, tags)

        # Note: Old sphinx projects have been configured as "language = None" because
        #       sphinx-quickstart previously generated this by default.
        #       To keep compatibility, they should be fallback to 'en' for a while
        #       (This conversion should not be removed before 2025-01-01).
        if namespace.get("language", ...) is None:
            logger.warning(__("Invalid configuration value found: 'language = None'. "
                              "Update your configuration to a valid language code. "
                              "Falling back to 'en' (English)."))
            namespace["language"] = "en"

        return cls(namespace, overrides or {})

    def convert_overrides(self, name: str, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        else:
            defvalue = self.values[name][0]
            if self.values[name][2] == Any:
                return value
            elif self.values[name][2] == {bool, str}:
                if value == '0':
                    # given falsy string from command line option
                    return False
                elif value == '1':
                    return True
                else:
                    return value
            elif type(defvalue) is bool or self.values[name][2] == [bool]:
                if value == '0':
                    # given falsy string from command line option
                    return False
                else:
                    return bool(value)
            elif isinstance(defvalue, dict):
                raise ValueError(__('cannot override dictionary config setting %r, '
                                    'ignoring (use %r to set individual elements)') %
                                 (name, name + '.key=value'))
            elif isinstance(defvalue, list):
                return value.split(',')
            elif isinstance(defvalue, int):
                try:
                    return int(value)
                except ValueError as exc:
                    raise ValueError(__('invalid number %r for config value %r, ignoring') %
                                     (value, name)) from exc
            elif callable(defvalue):
                return value
            elif defvalue is not None and not isinstance(defvalue, str):
                raise ValueError(__('cannot override config setting %r with unsupported '
                                    'type, ignoring') % name)
            else:
                return value

    def pre_init_values(self) -> None:
        """
        Initialize some limited config variables before initializing i18n and loading
        extensions.
        """
        variables = ['needs_sphinx', 'suppress_warnings', 'language', 'locale_dirs']
        for name in variables:
            try:
                if name in self.overrides:
                    self.__dict__[name] = self.convert_overrides(name, self.overrides[name])
                elif name in self._raw_config:
                    self.__dict__[name] = self._raw_config[name]
            except ValueError as exc:
                logger.warning("%s", exc)

    def init_values(self) -> None:
        config = self._raw_config
        for valname, value in self.overrides.items():
            try:
                if '.' in valname:
                    realvalname, key = valname.split('.', 1)
                    config.setdefault(realvalname, {})[key] = value
                    continue
                if valname not in self.values:
                    logger.warning(__('unknown config value %r in override, ignoring'),
                                   valname)
                    continue
                if isinstance(value, str):
                    config[valname] = self.convert_overrides(valname, value)
                else:
                    config[valname] = value
            except ValueError as exc:
                logger.warning("%s", exc)
        for name in config:
            if name in self.values:
                self.__dict__[name] = config[name]

    def post_init_values(self) -> None:
        """
        Initialize additional config variables that are added after init_values() called.
        """
        config = self._raw_config
        for name in config:
            if name not in self.__dict__ and name in self.values:
                self.__dict__[name] = config[name]

        check_confval_types(None, self)

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)
        if name not in self.values:
            raise AttributeError(__('No such config value: %s') % name)
        default = self.values[name][0]
        if callable(default):
            return default(self)
        return default

    def __getitem__(self, name: str) -> Any:
        return getattr(self, name)

    def __setitem__(self, name: str, value: Any) -> None:
        setattr(self, name, value)

    def __delitem__(self, name: str) -> None:
        delattr(self, name)

    def __contains__(self, name: str) -> bool:
        return name in self.values

    def __iter__(self) -> Generator[ConfigValue, None, None]:
        for name, value in self.values.items():
            yield ConfigValue(name, getattr(self, name), value[1])

    def add(self, name: str, default: Any, rebuild: bool | str, types: Any) -> None:
        if name in self.values:
            raise ExtensionError(__('Config value %r already present') % name)
        self.values[name] = (default, rebuild, types)

    def filter(self, rebuild: str | Sequence[str]) -> Iterator[ConfigValue]:
        if isinstance(rebuild, str):
            rebuild = [rebuild]
        return (value for value in self if value.rebuild in rebuild)

    def __getstate__(self) -> dict:
        """Obtains serializable data for pickling."""
        # remove potentially pickling-problematic values from config
        __dict__ = {}
        for key, value in self.__dict__.items():
            if key.startswith('_') or not is_serializable(value):
                pass
            else:
                __dict__[key] = value

        # create a picklable copy of values list
        __dict__['values'] = {}
        for key, value in self.values.items():
            real_value = getattr(self, key)
            if not is_serializable(real_value):
                # omit unserializable value
                real_value = None

            # types column is also omitted
            __dict__['values'][key] = (real_value, value[1], None)

        return __dict__

    def __setstate__(self, state: dict) -> None:
        self.__dict__.update(state)


def eval_config_file(filename: str, tags: Tags | None) -> dict[str, Any]:
    """Evaluate a config file."""
    namespace: dict[str, Any] = {}
    namespace['__file__'] = filename
    namespace['tags'] = tags

    with chdir(path.dirname(filename)):
        # during executing config file, current dir is changed to ``confdir``.
        try:
            with open(filename, 'rb') as f:
                code = compile(f.read(), filename.encode(fs_encoding), 'exec')
                exec(code, namespace)  # NoQA: S102
        except SyntaxError as err:
            msg = __("There is a syntax error in your configuration file: %s\n")
            raise ConfigError(msg % err) from err
        except SystemExit as exc:
            msg = __("The configuration file (or one of the modules it imports) "
                     "called sys.exit()")
            raise ConfigError(msg) from exc
        except ConfigError:
            # pass through ConfigError from conf.py as is.  It will be shown in console.
            raise
        except Exception as exc:
            msg = __("There is a programmable error in your configuration file:\n\n%s")
            raise ConfigError(msg % traceback.format_exc()) from exc

    return namespace


def convert_source_suffix(app: Sphinx, config: Config) -> None:
    """Convert old styled source_suffix to new styled one.

    * old style: str or list
    * new style: a dict which maps from fileext to filetype
    """
    source_suffix = config.source_suffix
    if isinstance(source_suffix, str):
        # if str, considers as default filetype (None)
        #
        # The default filetype is determined on later step.
        # By default, it is considered as restructuredtext.
        config.source_suffix = {source_suffix: None}  # type: ignore[attr-defined]
    elif isinstance(source_suffix, (list, tuple)):
        # if list, considers as all of them are default filetype
        config.source_suffix = {s: None for s in source_suffix}  # type: ignore[attr-defined]
    elif not isinstance(source_suffix, dict):
        logger.warning(__("The config value `source_suffix' expects "
                          "a string, list of strings, or dictionary. "
                          "But `%r' is given." % source_suffix))


def convert_highlight_options(app: Sphinx, config: Config) -> None:
    """Convert old styled highlight_options to new styled one.

    * old style: options
    * new style: a dict which maps from language name to options
    """
    options = config.highlight_options
    if options and not all(isinstance(v, dict) for v in options.values()):
        # old styled option detected because all values are not dictionary.
        config.highlight_options = {config.highlight_language:  # type: ignore[attr-defined]
                                    options}


def init_numfig_format(app: Sphinx, config: Config) -> None:
    """Initialize :confval:`numfig_format`."""
    numfig_format = {'section': _('Section %s'),
                     'figure': _('Fig. %s'),
                     'table': _('Table %s'),
                     'code-block': _('Listing %s')}

    # override default labels by configuration
    numfig_format.update(config.numfig_format)
    config.numfig_format = numfig_format  # type: ignore[attr-defined]


def correct_copyright_year(_app: Sphinx, config: Config) -> None:
    """Correct values of copyright year that are not coherent with
    the SOURCE_DATE_EPOCH environment variable (if set)

    See https://reproducible-builds.org/specs/source-date-epoch/
    """
    if (source_date_epoch := getenv('SOURCE_DATE_EPOCH')) is None:
        return

    source_date_epoch_year = str(time.gmtime(int(source_date_epoch)).tm_year)

    for k in ('copyright', 'epub_copyright'):
        if k in config:
            value: str | Sequence[str] = config[k]
            if isinstance(value, str):
                config[k] = _substitute_copyright_year(value, source_date_epoch_year)
            else:
                items = (_substitute_copyright_year(x, source_date_epoch_year) for x in value)
                config[k] = type(value)(items)  # type: ignore[call-arg]


def _substitute_copyright_year(copyright_line: str, replace_year: str) -> str:
    """Replace the year in a single copyright line.

    Legal formats are:

    * ``YYYY``
    * ``YYYY,``
    * ``YYYY ``
    * ``YYYY-YYYY,``
    * ``YYYY-YYYY ``

    The final year in the string is replaced with ``replace_year``.
    """
    if len(copyright_line) < 4 or not copyright_line[:4].isdigit():
        return copyright_line

    if copyright_line[4:5] in {'', ' ', ','}:
        return replace_year + copyright_line[4:]

    if copyright_line[4] != '-':
        return copyright_line

    if copyright_line[5:9].isdigit() and copyright_line[9] in ' ,':
        return copyright_line[:5] + replace_year + copyright_line[9:]

    return copyright_line


def check_confval_types(app: Sphinx | None, config: Config) -> None:
    """Check all values for deviation from the default value's type, since
    that can result in TypeErrors all over the place NB.
    """
    for confval in config:
        default, rebuild, annotations = config.values[confval.name]

        if callable(default):
            default = default(config)  # evaluate default value
        if default is None and not annotations:
            continue  # neither inferable nor expliclitly annotated types

        if annotations is Any:
            # any type of value is accepted
            pass
        elif isinstance(annotations, ENUM):
            if not annotations.match(confval.value):
                msg = __("The config value `{name}` has to be a one of {candidates}, "
                         "but `{current}` is given.")
                logger.warning(msg.format(name=confval.name,
                                          current=confval.value,
                                          candidates=annotations.candidates), once=True)
        else:
            if type(confval.value) is type(default):
                continue
            if type(confval.value) in annotations:
                continue

            common_bases = (set(type(confval.value).__bases__ + (type(confval.value),)) &
                            set(type(default).__bases__))
            common_bases.discard(object)
            if common_bases:
                continue  # at least we share a non-trivial base class

            if annotations:
                msg = __("The config value `{name}' has type `{current.__name__}'; "
                         "expected {permitted}.")
                wrapped_annotations = [f"`{c.__name__}'" for c in annotations]
                if len(wrapped_annotations) > 2:
                    permitted = (", ".join(wrapped_annotations[:-1])
                                 + f", or {wrapped_annotations[-1]}")
                else:
                    permitted = " or ".join(wrapped_annotations)
                logger.warning(msg.format(name=confval.name,
                                          current=type(confval.value),
                                          permitted=permitted), once=True)
            else:
                msg = __("The config value `{name}' has type `{current.__name__}', "
                         "defaults to `{default.__name__}'.")
                logger.warning(msg.format(name=confval.name,
                                          current=type(confval.value),
                                          default=type(default)), once=True)


def check_primary_domain(app: Sphinx, config: Config) -> None:
    primary_domain = config.primary_domain
    if primary_domain and not app.registry.has_domain(primary_domain):
        logger.warning(__('primary_domain %r not found, ignored.'), primary_domain)
        config.primary_domain = None  # type: ignore[attr-defined]


def check_root_doc(app: Sphinx, env: BuildEnvironment, added: set[str],
                   changed: set[str], removed: set[str]) -> set[str]:
    """Adjust root_doc to 'contents' to support an old project which does not have
    any root_doc setting.
    """
    if (app.config.root_doc == 'index' and
            'index' not in app.project.docnames and
            'contents' in app.project.docnames):
        logger.warning(__('Since v2.0, Sphinx uses "index" as root_doc by default. '
                          'Please add "root_doc = \'contents\'" to your conf.py.'))
        app.config.root_doc = "contents"  # type: ignore[attr-defined]

    return changed


def setup(app: Sphinx) -> dict[str, Any]:
    app.connect('config-inited', convert_source_suffix, priority=800)
    app.connect('config-inited', convert_highlight_options, priority=800)
    app.connect('config-inited', init_numfig_format, priority=800)
    app.connect('config-inited', correct_copyright_year, priority=800)
    app.connect('config-inited', check_confval_types, priority=800)
    app.connect('config-inited', check_primary_domain, priority=800)
    app.connect('env-get-outdated', check_root_doc)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
