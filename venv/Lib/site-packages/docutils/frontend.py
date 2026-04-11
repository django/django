# $Id: frontend.py 10196 2025-08-07 06:35:37Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Command-line and common processing for Docutils front-end tools.

This module is provisional.
Major changes will happen with the transition from the
"optparse" module to "arparse" in Docutils 2.0 or later.

Applications should use the high-level API provided by `docutils.core`.
See https://docutils.sourceforge.io/docs/api/runtime-settings.html.

Exports the following classes:

* `OptionParser`: Standard Docutils command-line processing.
  Deprecated. Will be replaced by an ArgumentParser.
* `Option`: Customized version of `optparse.Option`; validation support.
  Deprecated. Will be removed.
* `Values`: Runtime settings; objects are simple structs
  (``object.attribute``).  Supports cumulative list settings (attributes).
  Deprecated. Will be removed.
* `ConfigParser`: Standard Docutils config file processing.
  Provisional. Details will change.

Also exports the following functions:

Interface function:
  `get_default_settings()`.  New in 0.19.

Option callbacks:
  `store_multiple()`, `read_config_file()`. Deprecated. To be removed.

Setting validators:
  `validate_encoding()`, `validate_encoding_error_handler()`,
  `validate_encoding_and_error_handler()`,
  `validate_boolean()`, `validate_ternary()`,
  `validate_nonnegative_int()`, `validate_threshold()`,
  `validate_colon_separated_string_list()`,
  `validate_comma_separated_list()`,
  `validate_url_trailing_slash()`,
  `validate_dependency_file()`,
  `validate_strip_class()`
  `validate_smartquotes_locales()`.

  Provisional.

Misc:
  `make_paths_absolute()`, `filter_settings_spec()`. Provisional.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'


import codecs
import configparser
import optparse
import os
import os.path
import sys
import warnings
from optparse import SUPPRESS_HELP
from pathlib import Path

import docutils
from docutils import io, utils

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from typing import Any, ClassVar, Literal, Protocol

    from docutils import SettingsSpec, _OptionTuple, _SettingsSpecTuple
    from docutils.io import StrPath

    class _OptionValidator(Protocol):
        def __call__(
            self,
            setting: str,
            value: str | None,
            option_parser: OptionParser,
            /,
            config_parser: ConfigParser | None = None,
            config_section: str | None = None,
        ) -> Any:
            ...


def store_multiple(option: optparse.Option,
                   opt: str,
                   value: Any,
                   parser: OptionParser,
                   *args: str,
                   **kwargs: Any,
                   ) -> None:
    """
    Store multiple values in `parser.values`.  (Option callback.)

    Store `None` for each attribute named in `args`, and store the value for
    each key (attribute name) in `kwargs`.

    Deprecated. Will be removed with the switch to from optparse to argparse.
    """
    for attribute in args:
        setattr(parser.values, attribute, None)
    for key, value in kwargs.items():
        setattr(parser.values, key, value)


def read_config_file(option: optparse.Option,
                     opt: str,
                     value: Any,
                     parser: OptionParser,
                     ) -> None:
    """
    Read a configuration file during option processing.  (Option callback.)

    Deprecated. Will be removed with the switch to from optparse to argparse.
    """
    try:
        new_settings = parser.get_config_file_settings(value)
    except ValueError as err:
        parser.error(err)
    parser.values.update(new_settings, parser)


def validate_encoding(setting: str,
                      value: str | None = None,
                      option_parser: OptionParser | None = None,
                      config_parser: ConfigParser | None = None,
                      config_section: str | None = None,
                      ) -> str | None:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    if value == '':
        warnings.warn('Input encoding detection will be removed and the '
                      'special encoding values None and "" become invalid '
                      'in Docutils 1.0.', FutureWarning, stacklevel=2)
        return None
    try:
        codecs.lookup(value)
    except LookupError:
        prefix = f'setting "{setting}":' if setting else ''
        raise LookupError(f'{prefix} unknown encoding: "{value}"')
    return value


def validate_encoding_error_handler(
        setting: str,
        value: str | None = None,
        option_parser: OptionParser | None = None,
        config_parser: ConfigParser | None = None,
        config_section: str | None = None,
        ) -> str:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    try:
        codecs.lookup_error(value)
    except LookupError:
        raise LookupError(
            'unknown encoding error handler: "%s" (choices: '
            '"strict", "ignore", "replace", "backslashreplace", '
            '"xmlcharrefreplace", and possibly others; see documentation for '
            'the Python ``codecs`` module)' % value)
    return value


def validate_encoding_and_error_handler(
        setting: str,
        value: str | None = None,
        option_parser: OptionParser | None = None,
        config_parser: ConfigParser | None = None,
        config_section: str | None = None,
        ) -> str:
    """Check/normalize encoding settings

    Side-effect: if an error handler is included in the value, it is inserted
    into the appropriate place as if it were a separate setting/option.

    All arguments except `value` are ignored
    (kept for compatibility with "optparse" module).
    If there is only one positional argument, it is interpreted as `value`.
    """
    if ':' in value:
        encoding, handler = value.split(':')
        validate_encoding_error_handler(handler)
        if config_parser:
            config_parser.set(config_section, setting + '_error_handler',
                              handler)
        else:
            setattr(option_parser.values, setting + '_error_handler', handler)
    else:
        encoding = value
    return validate_encoding(encoding)


def validate_boolean(setting: str | bool,
                     value: str | None = None,
                     option_parser: OptionParser | None = None,
                     config_parser: ConfigParser | None = None,
                     config_section: str | None = None,
                     ) -> bool:
    """Check/normalize boolean settings:

    :True:  '1', 'on', 'yes', 'true'
    :False: '0', 'off', 'no','false', ''

    All arguments except `value` are ignored
    (kept for compatibility with "optparse" module).
    If there is only one positional argument, it is interpreted as `value`.
    """
    if value is None:
        value = setting
    if isinstance(value, bool):
        return value
    try:
        return OptionParser.booleans[value.strip().lower()]
    except KeyError:
        raise LookupError('unknown boolean value: "%s"' % value)


def validate_ternary(setting: str | bool,
                     value: str | None = None,
                     option_parser: OptionParser | None = None,
                     config_parser: ConfigParser | None = None,
                     config_section: str | None = None,
                     ) -> str | bool | None:
    """Check/normalize three-value settings:

    :True:  '1', 'on', 'yes', 'true'
    :False: '0', 'off', 'no','false', ''
    :any other value: returned as-is.

    All arguments except `value` are ignored
    (kept for compatibility with "optparse" module).
    If there is only one positional argument, it is interpreted as `value`.
    """
    if value is None:
        value = setting
    if isinstance(value, bool) or value is None:
        return value
    try:
        return OptionParser.booleans[value.strip().lower()]
    except KeyError:
        return value


def validate_nonnegative_int(setting: str | int,
                             value: str | None = None,
                             option_parser: OptionParser | None = None,
                             config_parser: ConfigParser | None = None,
                             config_section: str | None = None,
                             ) -> int:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    value = int(value)
    if value < 0:
        raise ValueError('negative value; must be positive or zero')
    return value


def validate_threshold(setting: str | int,
                       value: str | None = None,
                       option_parser: OptionParser | None = None,
                       config_parser: ConfigParser | None = None,
                       config_section: str | None = None,
                       ) -> int:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    try:
        return int(value)
    except ValueError:
        try:
            return OptionParser.thresholds[value.lower()]
        except (KeyError, AttributeError):
            raise LookupError('unknown threshold: %r.' % value)


def validate_colon_separated_string_list(
        setting: str | list[str],
        value: str | None = None,
        option_parser: OptionParser | None = None,
        config_parser: ConfigParser | None = None,
        config_section: str | None = None,
        ) -> list[str]:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    if not isinstance(value, list):
        value = value.split(':')
    else:
        last = value.pop()
        value.extend(last.split(':'))
    return value


def validate_comma_separated_list(
        setting: str | list[str],
        value: str | None = None,
        option_parser: OptionParser | None = None,
        config_parser: ConfigParser | None = None,
        config_section: str | None = None,
        ) -> list[str]:
    """Check/normalize list arguments (split at "," and strip whitespace).

    All arguments except `value` are ignored
    (kept for compatibility with "optparse" module).
    If there is only one positional argument, it is interpreted as `value`.
    """
    if value is None:
        value = setting
    # `value` may be ``bytes``, ``str``, or a ``list`` (when  given as
    # command line option and "action" is "append").
    if not isinstance(value, list):
        value = [value]
    # this function is called for every option added to `value`
    # -> split the last item and append the result:
    last = value.pop()
    items = [i.strip(' \t\n') for i in last.split(',') if i.strip(' \t\n')]
    value.extend(items)
    return value


def validate_math_output(setting: str,
                         value: str | None = None,
                         option_parser: OptionParser | None = None,
                         config_parser: ConfigParser | None = None,
                         config_section: str | None = None,
                         ) -> tuple[()] | tuple[str, str]:
    """Check "math-output" setting, return list with "format" and "options".

    See also https://docutils.sourceforge.io/docs/user/config.html#math-output

    Argument list for compatibility with "optparse" module.
    All arguments except `value` are ignored.
    If there is only one positional argument, it is interpreted as `value`.
    """
    if value is None:
        value = setting

    formats = ('html', 'latex', 'mathml', 'mathjax')
    tex2mathml_converters = ('', 'latexml', 'ttm', 'blahtexml', 'pandoc')

    if not value:
        return ()
    values = value.split(maxsplit=1)
    format = values[0].lower()
    try:
        options = values[1]
    except IndexError:
        options = ''
    if format not in formats:
        raise LookupError(f'Unknown math output format: "{value}",\n'
                          f'    choose from {formats}.')
    if format == 'mathml':
        converter = options.lower()
        if converter not in tex2mathml_converters:
            raise LookupError(f'MathML converter "{options}" not supported,\n'
                              f'    choose from {tex2mathml_converters}.')
        options = converter
    return format, options


def validate_url_trailing_slash(setting: str | None,
                                value: str | None = None,
                                option_parser: OptionParser | None = None,
                                config_parser: ConfigParser | None = None,
                                config_section: str | None = None,
                                ) -> str:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    if not value:
        return './'
    elif value.endswith('/'):
        return value
    else:
        return value + '/'


def validate_dependency_file(setting: str | None,
                             value: str | None = None,
                             option_parser: OptionParser | None = None,
                             config_parser: ConfigParser | None = None,
                             config_section: str | None = None,
                             ) -> utils.DependencyList:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    try:
        return utils.DependencyList(value)
    except OSError:
        # TODO: warn/info?
        return utils.DependencyList(None)


def validate_strip_class(setting: str,
                         value: str | None = None,
                         option_parser: OptionParser | None = None,
                         config_parser: ConfigParser | None = None,
                         config_section: str | None = None,
                         ) -> list[str]:
    # All arguments except `value` are ignored
    # (kept for compatibility with "optparse" module).
    # If there is only one positional argument, it is interpreted as `value`.
    if value is None:
        value = setting
    # value is a comma separated string list:
    value = validate_comma_separated_list(value)
    # validate list elements:
    for cls in value:
        normalized = docutils.nodes.make_id(cls)
        if cls != normalized:
            raise ValueError('Invalid class value %r (perhaps %r?)'
                             % (cls, normalized))
    return value


def validate_smartquotes_locales(
        setting: str | list[str | tuple[str, str]],
        value: str | None = None,
        option_parser: OptionParser | None = None,
        config_parser: ConfigParser | None = None,
        config_section: str | None = None,
        ) -> list[tuple[str, Sequence[str]]]:
    """Check/normalize a comma separated list of smart quote definitions.

    Return a list of (language-tag, quotes) string tuples.

    All arguments except `value` are ignored
    (kept for compatibility with "optparse" module).
    If there is only one positional argument, it is interpreted as `value`.
    """
    if value is None:
        value = setting
    # value is a comma separated string list:
    value = validate_comma_separated_list(value)
    # validate list elements
    lc_quotes = []
    for item in value:
        try:
            lang, quotes = item.split(':', 1)
        except AttributeError:
            # this function is called for every option added to `value`
            # -> ignore if already a tuple:
            lc_quotes.append(item)
            continue
        except ValueError:
            raise ValueError('Invalid value "%s".'
                             ' Format is "<language>:<quotes>".'
                             % item.encode('ascii', 'backslashreplace'))
        # parse colon separated string list:
        quotes = quotes.strip()
        multichar_quotes = quotes.split(':')
        if len(multichar_quotes) == 4:
            quotes = multichar_quotes
        elif len(quotes) != 4:
            raise ValueError('Invalid value "%s". Please specify 4 quotes\n'
                             '    (primary open/close; secondary open/close).'
                             % item.encode('ascii', 'backslashreplace'))
        lc_quotes.append((lang, quotes))
    return lc_quotes


def make_paths_absolute(pathdict: dict[str, list[StrPath] | StrPath],
                        keys: tuple[str],
                        base_path: StrPath | None = None,
                        ) -> None:
    """
    Interpret filesystem path settings relative to the `base_path` given.

    Paths are values in `pathdict` whose keys are in `keys`.  Get `keys` from
    `OptionParser.relative_path_settings`.
    """
    if base_path is None:
        base_path = Path.cwd()
    else:
        base_path = Path(base_path)
        if sys.platform == 'win32' and sys.version_info[:2] <= (3, 9):
            base_path = base_path.absolute()
    for key in keys:
        if key in pathdict:
            value = pathdict[key]
            if isinstance(value, (list, tuple)):
                value = [str((base_path/path).resolve()) for path in value]
            elif value:
                value = str((base_path/value).resolve())
            pathdict[key] = value


def make_one_path_absolute(base_path: StrPath, path: StrPath) -> str:
    # deprecated, will be removed
    warnings.warn('frontend.make_one_path_absolute() will be removed '
                  'in Docutils 2.0 or later.',
                  DeprecationWarning, stacklevel=2)
    return os.path.abspath(os.path.join(base_path, path))


def filter_settings_spec(settings_spec: _SettingsSpecTuple,
                         *exclude: str,
                         **replace: _OptionTuple,
                         ) -> _SettingsSpecTuple:
    """Return a copy of `settings_spec` excluding/replacing some settings.

    `settings_spec` is a tuple of configuration settings
    (cf. `docutils.SettingsSpec.settings_spec`).

    Optional positional arguments are names of to-be-excluded settings.
    Keyword arguments are option specification replacements.
    (See the html4strict writer for an example.)
    """
    settings = list(settings_spec)
    # every third item is a sequence of option tuples
    for i in range(2, len(settings), 3):
        newopts: list[_OptionTuple] = []
        for opt_spec in settings[i]:
            # opt_spec is ("<help>", [<option strings>], {<keyword args>})
            opt_name = [opt_string[2:].replace('-', '_')
                        for opt_string in opt_spec[1]
                        if opt_string.startswith('--')][0]
            if opt_name in exclude:
                continue
            if opt_name in replace.keys():
                newopts.append(replace[opt_name])
            else:
                newopts.append(opt_spec)
        settings[i] = tuple(newopts)
    return tuple(settings)


class Values(optparse.Values):
    """Storage for option values.

    Updates list attributes by extension rather than by replacement.
    Works in conjunction with the `OptionParser.lists` instance attribute.

    Deprecated. Will be removed when switching to the "argparse" module.
    """

    def __init__(self, defaults: dict[str, Any] | None = None) -> None:
        warnings.warn('frontend.Values class will be removed '
                      'in Docutils 2.0 or later.',
                      DeprecationWarning, stacklevel=2)
        super().__init__(defaults=defaults)
        if getattr(self, 'record_dependencies', None) is None:
            # Set up dummy dependency list.
            self.record_dependencies = utils.DependencyList()

    def update(self,
               other_dict: Values | Mapping[str, Any],
               option_parser: OptionParser,
               ) -> None:
        if isinstance(other_dict, Values):
            other_dict = other_dict.__dict__
        other_dict = dict(other_dict)  # also works with ConfigParser sections
        for setting in option_parser.lists.keys():
            if hasattr(self, setting) and setting in other_dict:
                value = getattr(self, setting)
                if value:
                    value += other_dict[setting]
                    del other_dict[setting]
        self._update_loose(other_dict)

    def copy(self) -> Values:
        """Return a shallow copy of `self`."""
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            return self.__class__(defaults=self.__dict__)

    def setdefault(self, name: str, default: Any) -> Any:
        """Return ``self.name`` or ``default``.

        If ``self.name`` is unset, set ``self.name = default``.
        """
        if getattr(self, name, None) is None:
            setattr(self, name, default)
        return getattr(self, name)


class Option(optparse.Option):
    """Add validation and override support to `optparse.Option`.

    Deprecated. Will be removed.
    """

    ATTRS = optparse.Option.ATTRS + ['validator', 'overrides']

    validator: _OptionValidator
    overrides: str | None

    def __init__(self, *args: str | None, **kwargs: Any) -> None:
        warnings.warn('The frontend.Option class will be removed '
                      'in Docutils 2.0 or later.',
                      DeprecationWarning, stacklevel=2)
        super().__init__(*args, **kwargs)

    def process(self,
                opt: str,
                value: Any,
                values: Values,
                parser: OptionParser,
                ) -> int:
        """
        Call the validator function on applicable settings and
        evaluate the 'overrides' option.
        Extends `optparse.Option.process`.
        """
        result = super().process(opt, value, values, parser)
        setting = self.dest
        if setting:
            if self.validator:
                value = getattr(values, setting)
                try:
                    new_value = self.validator(setting, value, parser)
                except Exception as err:
                    raise optparse.OptionValueError(
                        'Error in option "%s":\n    %s'
                        % (opt, io.error_string(err)))
                setattr(values, setting, new_value)
            if self.overrides:
                setattr(values, self.overrides, None)
        return result


class OptionParser(optparse.OptionParser, docutils.SettingsSpec):
    """
    Settings parser for command-line and library use.

    The `settings_spec` specification here and in other Docutils components
    are merged to build the set of command-line options and runtime settings
    for this process.

    Common settings (defined below) and component-specific settings must not
    conflict.  Short options are reserved for common settings, and components
    are restricted to using long options.

    Deprecated.
    Will be replaced by a subclass of `argparse.ArgumentParser`.
    """

    standard_config_files: ClassVar[list[str]] = [
        '/etc/docutils.conf',           # system-wide
        './docutils.conf',              # project-specific
        '~/.docutils']                  # user-specific
    """Docutils configuration files, using ConfigParser syntax.

    Filenames will be tilde-expanded later. Later files override earlier ones.
    """

    threshold_choices: ClassVar[tuple[str]] = (
        'info', '1', 'warning', '2', 'error', '3', 'severe', '4', 'none', '5')
    """Possible inputs for for --report and --halt threshold values."""

    thresholds: ClassVar[dict[str, int]] = {
        'info': 1, 'warning': 2, 'error': 3, 'severe': 4, 'none': 5}
    """Lookup table for --report and --halt threshold values."""

    booleans: ClassVar[dict[str, bool]] = {
        '1': True, 'on': True, 'yes': True, 'true': True,
        '0': False, 'off': False, 'no': False, 'false': False, '': False}
    """Lookup table for boolean configuration file settings."""

    default_error_encoding: ClassVar[str] = (
        getattr(sys.stderr, 'encoding', None)
        or io._locale_encoding
        or 'ascii')

    default_error_encoding_error_handler: ClassVar[str] = 'backslashreplace'

    settings_spec = (
        'General Docutils Options',
        None,
        (('Output destination name. Obsoletes the <destination> '
          'positional argument. Default: None (stdout).',
          ['--output-path', '--output'], {'metavar': '<destination>'}),
         ('Specify the document title as metadata.',
          ['--title'], {'metavar': '<title>'}),
         ('Include a "Generated by Docutils" credit and link.',
          ['--generator', '-g'], {'action': 'store_true',
                                  'validator': validate_boolean}),
         ('Do not include a generator credit.',
          ['--no-generator'], {'action': 'store_false', 'dest': 'generator'}),
         ('Include the date at the end of the document (UTC).',
          ['--date', '-d'], {'action': 'store_const', 'const': '%Y-%m-%d',
                             'dest': 'datestamp'}),
         ('Include the time & date (UTC).',
          ['--time', '-t'], {'action': 'store_const',
                             'const': '%Y-%m-%d %H:%M UTC',
                             'dest': 'datestamp'}),
         ('Do not include a datestamp of any kind.',
          ['--no-datestamp'], {'action': 'store_const', 'const': None,
                               'dest': 'datestamp'}),
         ('Base directory for absolute paths when reading '
          'from the local filesystem. Default "".',
          ['--root-prefix'],
          {'default': '', 'metavar': '<path>'}),
         ('Include a "View document source" link.',
          ['--source-link', '-s'], {'action': 'store_true',
                                    'validator': validate_boolean}),
         ('Use <URL> for a source link; implies --source-link.',
          ['--source-url'], {'metavar': '<URL>'}),
         ('Do not include a "View document source" link.',
          ['--no-source-link'],
          {'action': 'callback', 'callback': store_multiple,
           'callback_args': ('source_link', 'source_url')}),
         ('Link from section headers to TOC entries.  (default)',
          ['--toc-entry-backlinks'],
          {'dest': 'toc_backlinks', 'action': 'store_const', 'const': 'entry',
           'default': 'entry'}),
         ('Link from section headers to the top of the TOC.',
          ['--toc-top-backlinks'],
          {'dest': 'toc_backlinks', 'action': 'store_const', 'const': 'top'}),
         ('Disable backlinks to the table of contents.',
          ['--no-toc-backlinks'],
          {'dest': 'toc_backlinks', 'action': 'store_false'}),
         ('Link from footnotes/citations to references. (default)',
          ['--footnote-backlinks'],
          {'action': 'store_true', 'default': True,
           'validator': validate_boolean}),
         ('Disable backlinks from footnotes and citations.',
          ['--no-footnote-backlinks'],
          {'dest': 'footnote_backlinks', 'action': 'store_false'}),
         ('Enable section numbering by Docutils.  (default)',
          ['--section-numbering'],
          {'action': 'store_true', 'dest': 'sectnum_xform',
           'default': True, 'validator': validate_boolean}),
         ('Disable section numbering by Docutils.',
          ['--no-section-numbering'],
          {'action': 'store_false', 'dest': 'sectnum_xform'}),
         ('Remove comment elements from the document tree.',
          ['--strip-comments'],
          {'action': 'store_true', 'validator': validate_boolean}),
         ('Leave comment elements in the document tree. (default)',
          ['--leave-comments'],
          {'action': 'store_false', 'dest': 'strip_comments'}),
         ('Remove all elements with classes="<class>" from the document tree. '
          'Warning: potentially dangerous; use with caution. '
          '(Multiple-use option.)',
          ['--strip-elements-with-class'],
          {'action': 'append', 'dest': 'strip_elements_with_classes',
           'metavar': '<class>', 'validator': validate_strip_class}),
         ('Remove all classes="<class>" attributes from elements in the '
          'document tree. Warning: potentially dangerous; use with caution. '
          '(Multiple-use option.)',
          ['--strip-class'],
          {'action': 'append', 'dest': 'strip_classes',
           'metavar': '<class>', 'validator': validate_strip_class}),
         ('Report system messages at or higher than <level>: "info" or "1", '
          '"warning"/"2" (default), "error"/"3", "severe"/"4", "none"/"5"',
          ['--report', '-r'], {'choices': threshold_choices, 'default': 2,
                               'dest': 'report_level', 'metavar': '<level>',
                               'validator': validate_threshold}),
         ('Report all system messages.  (Same as "--report=1".)',
          ['--verbose', '-v'], {'action': 'store_const', 'const': 1,
                                'dest': 'report_level'}),
         ('Report no system messages.  (Same as "--report=5".)',
          ['--quiet', '-q'], {'action': 'store_const', 'const': 5,
                              'dest': 'report_level'}),
         ('Halt execution at system messages at or above <level>.  '
          'Levels as in --report.  Default: 4 (severe).',
          ['--halt'], {'choices': threshold_choices, 'dest': 'halt_level',
                       'default': 4, 'metavar': '<level>',
                       'validator': validate_threshold}),
         ('Halt at the slightest problem.  Same as "--halt=info".',
          ['--strict'], {'action': 'store_const', 'const': 1,
                         'dest': 'halt_level'}),
         ('Enable a non-zero exit status for non-halting system messages at '
          'or above <level>.  Default: 5 (disabled).',
          ['--exit-status'], {'choices': threshold_choices,
                              'dest': 'exit_status_level',
                              'default': 5, 'metavar': '<level>',
                              'validator': validate_threshold}),
         ('Enable debug-level system messages and diagnostics.',
          ['--debug'], {'action': 'store_true',
                        'validator': validate_boolean}),
         ('Disable debug output.  (default)',
          ['--no-debug'], {'action': 'store_false', 'dest': 'debug'}),
         ('Send the output of system messages to <file>.',
          ['--warnings'], {'dest': 'warning_stream', 'metavar': '<file>'}),
         ('Enable Python tracebacks when Docutils is halted.',
          ['--traceback'], {'action': 'store_true', 'default': None,
                            'validator': validate_boolean}),
         ('Disable Python tracebacks.  (default)',
          ['--no-traceback'], {'dest': 'traceback', 'action': 'store_false'}),
         ('Specify the encoding and optionally the '
          'error handler of input text.  Default: utf-8.',
          ['--input-encoding'],
          {'metavar': '<name[:handler]>', 'default': 'utf-8',
           'validator': validate_encoding_and_error_handler}),
         (SUPPRESS_HELP, ['--input-encoding-error-handler'],
          {'default': 'strict', 'validator': validate_encoding_error_handler}),
         ('Specify the text encoding and optionally the error handler for '
          'output.  Default: utf-8.',
          ['--output-encoding'],
          {'metavar': '<name[:handler]>', 'default': 'utf-8',
           'validator': validate_encoding_and_error_handler}),
         (SUPPRESS_HELP, ['--output-encoding-error-handler'],
          {'default': 'strict', 'validator': validate_encoding_error_handler}),
         ('Specify text encoding and optionally the error handler'
          f' for error output.  Default: {default_error_encoding}.',
          ['--error-encoding', '-e'],
          {'metavar': '<name[:handler]>', 'default': default_error_encoding,
           'validator': validate_encoding_and_error_handler}),
         (SUPPRESS_HELP, ['--error-encoding-error-handler'],
          {'default': default_error_encoding_error_handler,
           'validator': validate_encoding_error_handler}),
         ('Specify the language (as BCP 47 language tag).  Default: en.',
          ['--language', '-l'], {'dest': 'language_code', 'default': 'en',
                                 'metavar': '<tag>'}),
         ('Write output file dependencies to <file>.',
          ['--record-dependencies'],
          {'metavar': '<file>', 'validator': validate_dependency_file,
           'default': None}),           # default set in Values class
         ('Read configuration settings from <file>, if it exists.',
          ['--config'], {'metavar': '<file>', 'type': 'string',
                         'action': 'callback', 'callback': read_config_file}),
         ("Show this program's version number and exit.",
          ['--version', '-V'], {'action': 'version'}),
         ('Show this help message and exit.',
          ['--help', '-h'], {'action': 'help'}),
         # Typically not useful for non-programmatical use:
         (SUPPRESS_HELP, ['--id-prefix'], {'default': ''}),
         (SUPPRESS_HELP, ['--auto-id-prefix'], {'default': '%'}),
         # Hidden options, for development use only:
         (SUPPRESS_HELP, ['--dump-settings'], {'action': 'store_true'}),
         (SUPPRESS_HELP, ['--dump-internals'], {'action': 'store_true'}),
         (SUPPRESS_HELP, ['--dump-transforms'], {'action': 'store_true'}),
         (SUPPRESS_HELP, ['--dump-pseudo-xml'], {'action': 'store_true'}),
         (SUPPRESS_HELP, ['--expose-internal-attribute'],
          {'action': 'append', 'dest': 'expose_internals',
           'validator': validate_colon_separated_string_list}),
         (SUPPRESS_HELP, ['--strict-visitor'], {'action': 'store_true'}),
         ))
    """Runtime settings and command-line options common to all Docutils front
    ends.  Setting specs specific to individual Docutils components are also
    used (see `populate_from_components()`)."""

    settings_defaults = {'_disable_config': None,
                         '_source': None,
                         '_destination': None,
                         '_config_files': None}
    """Defaults for settings without command-line option equivalents.

    See https://docutils.sourceforge.io/docs/user/config.html#internal-settings
    """

    relative_path_settings: tuple[str, ...] = ()  # will be modified

    config_section = 'general'

    version_template: ClassVar[str] = '%%prog (Docutils %s%s, Python %s, on %s)' % (  # NoQA: E501
        docutils.__version__,
        (details := docutils.__version_details__) and f' [{details}]' or '',
        sys.version.split()[0],
        sys.platform)
    """Default version message."""

    def __init__(self,
                 components: Iterable[SettingsSpec] = (),
                 defaults: Mapping[str, Any] | None = None,
                 read_config_files: bool | None = False,
                 *args,
                 **kwargs,
                 ) -> None:
        """Set up OptionParser instance.

        `components` is a list of Docutils components each containing a
        ``.settings_spec`` attribute.
        `defaults` is a mapping of setting default overrides.
        """

        self.lists: dict[str, Literal[True]] = {}
        """Set of list-type settings."""

        self.config_files: list[str] = []
        """List of paths of applied configuration files."""

        self.relative_path_settings = ('warning_stream',)  # will be modified

        warnings.warn(
            'The frontend.OptionParser class will be replaced by a subclass '
            'of argparse.ArgumentParser in Docutils 2.0 or later.\n  '
            'To get default settings, use frontend.get_default_settings().',
            DeprecationWarning, stacklevel=2)
        super().__init__(option_class=Option, add_help_option=False,
                         formatter=optparse.TitledHelpFormatter(width=78),
                         *args, **kwargs)
        if not self.version:
            self.version = self.version_template
        self.components: tuple[SettingsSpec, ...] = (self, *components)
        self.populate_from_components(self.components)
        self.defaults.update(defaults or {})
        if read_config_files and not self.defaults['_disable_config']:
            try:
                config_settings = self.get_standard_config_settings()
            except ValueError as err:
                self.error(str(err))
            self.defaults.update(config_settings.__dict__)

    def populate_from_components(self, components: Iterable[SettingsSpec],
                                 ) -> None:
        """Collect settings specification from components.

        For each component, populate from the `SettingsSpec.settings_spec`
        structure, then from the `SettingsSpec.settings_defaults` dictionary.
        After all components have been processed, check for and populate from
        each component's `SettingsSpec.settings_default_overrides` dictionary.
        """
        for component in components:
            if component is None:
                continue
            settings_spec = component.settings_spec
            self.relative_path_settings += component.relative_path_settings
            for i in range(0, len(settings_spec), 3):
                title, description, option_spec = settings_spec[i:i+3]
                if title:
                    group = optparse.OptionGroup(self, title, description)
                    self.add_option_group(group)
                else:
                    group = self        # single options
                for (help_text, option_strings, kwargs) in option_spec:
                    option = group.add_option(help=help_text, *option_strings,
                                              **kwargs)
                    if kwargs.get('action') == 'append':
                        self.lists[option.dest] = True
                if component.settings_defaults:
                    self.defaults.update(component.settings_defaults)
        for component in components:
            if component and component.settings_default_overrides:
                self.defaults.update(component.settings_default_overrides)

    @classmethod
    def get_standard_config_files(cls) -> Sequence[StrPath]:
        """Return list of config files, from environment or standard."""
        if 'DOCUTILSCONFIG' in os.environ:
            config_files = os.environ['DOCUTILSCONFIG'].split(os.pathsep)
        else:
            config_files = cls.standard_config_files
        return [os.path.expanduser(f) for f in config_files if f.strip()]

    def get_standard_config_settings(self) -> Values:
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            settings = Values()
        for filename in self.get_standard_config_files():
            settings.update(self.get_config_file_settings(filename), self)
        return settings

    def get_config_file_settings(self, config_file: str) -> dict[str, Any]:
        """Returns a dictionary containing appropriate config file settings."""
        config_parser = ConfigParser()
        # parse config file, add filename if found and successfully read.
        applied = set()
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            self.config_files += config_parser.read(config_file, self)
            settings = Values()
        for component in self.components:
            if not component:
                continue
            for section in (tuple(component.config_section_dependencies or ())
                            + (component.config_section,)):
                if section in applied:
                    continue
                applied.add(section)
                if config_parser.has_section(section):
                    settings.update(config_parser[section], self)
        make_paths_absolute(settings.__dict__,
                            self.relative_path_settings,
                            os.path.dirname(config_file))
        return settings.__dict__

    def check_values(self, values: Values, args: list[str]) -> Values:
        """Store positional arguments as runtime settings."""
        values._source, values._destination = self.check_args(args)
        make_paths_absolute(values.__dict__, self.relative_path_settings)
        values._config_files = self.config_files
        return values

    def check_args(self, args: list[str]) -> tuple[str|None, str|None]:
        # provisional: argument handling will change, see RELEASE_NOTES
        source = destination = None
        if args:
            source = args.pop(0)
            if source == '-':           # means stdin
                source = None
        if args:
            destination = args.pop(0)
            if destination == '-':      # means stdout
                destination = None
        if args:
            self.error('Maximum 2 arguments allowed.')
        if source and source == destination:
            self.error('Do not specify the same file for both source and '
                       'destination.  It will clobber the source file.')
        return source, destination

    def get_default_values(self) -> Values:
        """Needed to get custom `Values` instances."""
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            defaults = Values(self.defaults)
        defaults._config_files = self.config_files
        return defaults

    def get_option_by_dest(self, dest: str) -> Option:
        """
        Get an option by its dest.

        If you're supplying a dest which is shared by several options,
        it is undefined which option of those is returned.

        A KeyError is raised if there is no option with the supplied
        dest.
        """
        for group in self.option_groups + [self]:
            for option in group.option_list:
                if option.dest == dest:
                    return option
        raise KeyError('No option with dest == %r.' % dest)


class ConfigParser(configparser.RawConfigParser):
    """Parser for Docutils configuration files.

    See https://docutils.sourceforge.io/docs/user/config.html.

    Option key normalization includes conversion of '-' to '_'.

    Config file encoding is "utf-8". Encoding errors are reported
    and the affected file(s) skipped.

    This class is provisional and will change in future versions.
    """

    old_settings: ClassVar[dict[str, tuple[str, str]]] = {
        'pep_stylesheet': ('pep_html writer', 'stylesheet'),
        'pep_stylesheet_path': ('pep_html writer', 'stylesheet_path'),
        'pep_template': ('pep_html writer', 'template')}
    """{old setting: (new section, new setting)} mapping, used by
    `handle_old_config`, to convert settings from the old [options] section.
    """

    old_warning: ClassVar[str] = (
        'The "[option]" section is deprecated.\n'
        'Support for old-format configuration files will be removed in '
        'Docutils 2.0.  Please revise your configuration files.  '
        'See <https://docutils.sourceforge.io/docs/user/config.html>, '
        'section "Old-Format Configuration Files".')

    not_utf8_error: ClassVar[str] = """\
Unable to read configuration file "%s": content not encoded as UTF-8.
Skipping "%s" configuration file.
"""

    def read(self,
             filenames: str | Sequence[str],
             option_parser: OptionParser | None = None,
             ) -> list[str]:
        # Currently, if a `docutils.frontend.OptionParser` instance is
        # supplied, setting values are validated.
        if option_parser is not None:
            warnings.warn('frontend.ConfigParser.read(): parameter '
                          '"option_parser" will be removed '
                          'in Docutils 2.0 or later.',
                          DeprecationWarning, stacklevel=2)
        read_ok = []
        if isinstance(filenames, str):
            filenames = [filenames]
        for filename in filenames:
            # Config files are UTF-8-encoded:
            try:
                read_ok += super().read(filename, encoding='utf-8')
            except UnicodeDecodeError:
                sys.stderr.write(self.not_utf8_error % (filename, filename))
                continue
            if 'options' in self:
                self.handle_old_config(filename)
            if option_parser is not None:
                self.validate_settings(filename, option_parser)
        return read_ok

    def handle_old_config(self, filename: str) -> None:
        warnings.warn_explicit(self.old_warning, ConfigDeprecationWarning,
                               filename, 0)
        try:
            options = dict(self['options'])
        except KeyError:
            options = {}
        if not self.has_section('general'):
            self.add_section('general')
        for key, value in options.items():
            if key in self.old_settings:
                section, setting = self.old_settings[key]
                if not self.has_section(section):
                    self.add_section(section)
            else:
                section = 'general'
                setting = key
            if not self.has_option(section, setting):
                self.set(section, setting, value)
        self.remove_section('options')

    def validate_settings(self, filename: str, option_parser: OptionParser,
                          ) -> None:
        """
        Call the validator function and implement overrides on all applicable
        settings.
        """
        for section in self.sections():
            for setting in self.options(section):
                try:
                    option = option_parser.get_option_by_dest(setting)
                except KeyError:
                    continue
                if option.validator:
                    value = self.get(section, setting)
                    try:
                        new_value = option.validator(
                            setting, value, option_parser,
                            config_parser=self, config_section=section)
                    except Exception as err:
                        raise ValueError(f'Error in config file "{filename}", '
                                         f'section "[{section}]":\n'
                                         f'    {io.error_string(err)}\n'
                                         f'        {setting} = {value}')
                    self.set(section, setting, new_value)
                if option.overrides:
                    self.set(section, option.overrides, None)

    def optionxform(self, optionstr: str) -> str:
        """
        Lowercase and transform '-' to '_'.

        So the cmdline form of option names can be used in config files.
        """
        return optionstr.lower().replace('-', '_')


class ConfigDeprecationWarning(FutureWarning):
    """Warning for deprecated configuration file features."""


def get_default_settings(*components: SettingsSpec) -> Values:
    """Return default runtime settings for `components`.

    Return a `frontend.Values` instance with defaults for generic Docutils
    settings and settings from the `components` (`SettingsSpec` instances).

    This corresponds to steps 1 and 2 in the `runtime settings priority`__.

    __ https://docutils.sourceforge.io/docs/api/runtime-settings.html
       #settings-priority
    """
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        return OptionParser(components).get_default_values()
