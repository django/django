# $Id: __init__.py 10250 2025-09-22 20:59:57Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
Miscellaneous utilities for the documentation utilities.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import itertools
import os
import os.path
import re
import sys
import unicodedata
import warnings
from pathlib import PurePath, Path

from docutils import ApplicationError, DataError
from docutils import io, nodes
# for backwards compatibility
from docutils.nodes import unescape  # noqa: F401 (imported but unused)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Sequence, Iterable
    from typing import Any, Final, Literal, TextIO

    from docutils.utils._typing import TypeAlias

    from docutils.nodes import StrPath
    from docutils.frontend import Values

    _ObserverFunc: TypeAlias = Callable[[nodes.system_message], None]


class SystemMessage(ApplicationError):

    def __init__(self, system_message: nodes.system_message, level: int,
                 ) -> None:
        Exception.__init__(self, system_message.astext())
        self.level = level


class SystemMessagePropagation(ApplicationError):
    pass


class Reporter:

    """
    Info/warning/error reporter and ``system_message`` element generator.

    Five levels of system messages are defined, along with corresponding
    methods: `debug()`, `info()`, `warning()`, `error()`, and `severe()`.

    There is typically one Reporter object per process.  A Reporter object is
    instantiated with thresholds for reporting (generating warnings) and
    halting processing (raising exceptions), a switch to turn debug output on
    or off, and an I/O stream for warnings.  These are stored as instance
    attributes.

    When a system message is generated, its level is compared to the stored
    thresholds, and a warning or error is generated as appropriate.  Debug
    messages are produced if the stored debug switch is on, independently of
    other thresholds.  Message output is sent to the stored warning stream if
    not set to ''.

    The Reporter class also employs a modified form of the "Observer" pattern
    [GoF95]_ to track system messages generated.  The `attach_observer` method
    should be called before parsing, with a bound method or function which
    accepts system messages.  The observer can be removed with
    `detach_observer`, and another added in its place.

    .. [GoF95] Gamma, Helm, Johnson, Vlissides. *Design Patterns: Elements of
       Reusable Object-Oriented Software*. Addison-Wesley, Reading, MA, USA,
       1995.
    """

    # Reporter.get_source_and_line is patched in by ``RSTState.runtime_init``
    get_source_and_line: Callable[[int|None], tuple[StrPath|None, int|None]]

    levels: Final[Sequence[str]] = (
        'DEBUG', 'INFO', 'WARNING', 'ERROR', 'SEVERE')
    """List of names for system message levels, indexed by level."""

    # system message level constants:
    DEBUG_LEVEL: Final = 0
    INFO_LEVEL: Final = 1
    WARNING_LEVEL: Final = 2
    ERROR_LEVEL: Final = 3
    SEVERE_LEVEL: Final = 4

    def __init__(
            self,
            source: StrPath,
            report_level: int,
            halt_level: int,
            stream: io.ErrorOutput|TextIO|str|Literal[False]|None = None,
            debug: bool = False,
            encoding: str|None = None,
            error_handler: str = 'backslashreplace',
            ) -> None:
        """Low level instantiating. See also `new_reporter().`.

        :Parameters:
            - `source`: The path to or description of the source data.
            - `report_level`: The level at or above which warning output will
              be sent to `stream`.
            - `halt_level`: The level at or above which `SystemMessage`
              exceptions will be raised, halting execution.
            - `debug`: Show debug (level=0) system messages?
            - `stream`: Where warning output is sent.  Can be file-like (has a
              ``.write`` method), a string (file name, opened for writing),
              '' (empty string) or `False` (for discarding all stream messages)
              or `None` (implies `sys.stderr`; default).
            - `encoding`: The output encoding.
            - `error_handler`: The error handler for stderr output encoding.
        """

        self.source = source
        """The path to or description of the source data."""

        self.error_handler = error_handler
        """The character encoding error handler."""

        self.debug_flag = debug
        """Show debug (level=0) system messages?"""

        self.report_level = report_level
        """The level at or above which warning output will be sent
        to `self.stream`."""

        self.halt_level = halt_level
        """The level at or above which `SystemMessage` exceptions
        will be raised, halting execution."""

        if not isinstance(stream, io.ErrorOutput):
            stream = io.ErrorOutput(stream, encoding, error_handler)

        self.stream: io.ErrorOutput = stream
        """Where warning output is sent."""

        self.encoding: str = encoding or getattr(stream, 'encoding', 'ascii')
        """The output character encoding."""

        self.observers: list[_ObserverFunc] = []
        """List of bound methods or functions to call with each system_message
        created."""

        self.max_level: int = -1
        """The highest level system message generated so far."""

    def attach_observer(self, observer: _ObserverFunc) -> None:
        """
        The `observer` parameter is a function or bound method which takes one
        argument, a `nodes.system_message` instance.
        """
        self.observers.append(observer)

    def detach_observer(self, observer: _ObserverFunc) -> None:
        self.observers.remove(observer)

    def notify_observers(self, message: nodes.system_message) -> None:
        for observer in self.observers:
            observer(message)

    def system_message(self,
                       level: int,
                       message: str,
                       *children,
                       **kwargs: Any
                       ) -> nodes.system_message:
        """
        Return a system_message object.

        Raise an exception or generate a warning if appropriate.
        """
        # `message` can be a `str` or `Exception` instance.
        if isinstance(message, Exception):
            message = str(message)

        attributes = kwargs.copy()
        if 'base_node' in kwargs:
            source, line = get_source_line(kwargs['base_node'])
            del attributes['base_node']
            if source is not None:
                attributes.setdefault('source', source)
            if line is not None:
                attributes.setdefault('line', line)
                # assert source is not None, "line- but no source-argument"
        if 'source' not in attributes:
            # 'line' is absolute line number
            try:
                source, line = self.get_source_and_line(attributes.get('line'))
            except AttributeError:
                source, line = None, None
            if source is not None:
                attributes['source'] = source
            if line is not None:
                attributes['line'] = line
        # assert attributes['line'] is not None, (message, kwargs)
        # assert attributes['source'] is not None, (message, kwargs)
        attributes.setdefault('source', self.source)

        msg = nodes.system_message(message, level=level,
                                   type=self.levels[level],
                                   *children, **attributes)
        if self.stream and (level >= self.report_level
                            or self.debug_flag and level == self.DEBUG_LEVEL
                            or level >= self.halt_level):
            self.stream.write(msg.astext() + '\n')
        if level >= self.halt_level:
            raise SystemMessage(msg, level)
        if level > self.DEBUG_LEVEL or self.debug_flag:
            self.notify_observers(msg)
        self.max_level = max(level, self.max_level)
        return msg

    def debug(self, *args, **kwargs: Any) -> nodes.system_message:
        """
        Level-0, "DEBUG": an internal reporting issue.

        Typically, there is no effect on the processing. Level-0 system
        messages are handled separately from the others.
        """
        if self.debug_flag:
            return self.system_message(self.DEBUG_LEVEL, *args, **kwargs)

    def info(self, *args, **kwargs: Any) -> nodes.system_message:
        """
        Level-1, "INFO": a minor issue that can be ignored.

        Typically, there is no effect on processing and level-1 system
        messages are not reported.
        """
        return self.system_message(self.INFO_LEVEL, *args, **kwargs)

    def warning(self, *args, **kwargs: Any) -> nodes.system_message:
        """
        Level-2, "WARNING": an issue that should be addressed.

        If ignored, there may be unpredictable problems with the output.
        """
        return self.system_message(self.WARNING_LEVEL, *args, **kwargs)

    def error(self, *args, **kwargs: Any) -> nodes.system_message:
        """
        Level-3, "ERROR": an error that should be addressed.

        If ignored, the output will contain errors.
        """
        return self.system_message(self.ERROR_LEVEL, *args, **kwargs)

    def severe(self, *args, **kwargs: Any) -> nodes.system_message:
        """
        Level-4, "SEVERE": a severe error that must be addressed.

        If ignored, the output will contain severe errors. Typically level-4
        system messages are turned into exceptions which halt processing.
        """
        return self.system_message(self.SEVERE_LEVEL, *args, **kwargs)


class ExtensionOptionError(DataError): pass  # NoQA: E701
class BadOptionError(ExtensionOptionError): pass  # NoQA: E701
class BadOptionDataError(ExtensionOptionError): pass  # NoQA: E701
class DuplicateOptionError(ExtensionOptionError): pass  # NoQA: E701


def extract_extension_options(field_list: nodes.field_list,
                              options_spec: dict[str, Callable[object], Any],
                              ) -> dict[str, Any]:
    """
    Return a dictionary mapping extension option names to converted values.

    :Parameters:
        - `field_list`: A flat field list without field arguments, where each
          field body consists of a single paragraph only.
        - `options_spec`: Dictionary mapping known option names to a
          conversion function such as `int` or `float`.

    :Exceptions:
        - `KeyError` for unknown option names.
        - `ValueError` for invalid option values (raised by the conversion
           function).
        - `TypeError` for invalid option value types (raised by conversion
           function).
        - `DuplicateOptionError` for duplicate options.
        - `BadOptionError` for invalid fields.
        - `BadOptionDataError` for invalid option data (missing name,
          missing data, bad quotes, etc.).
    """
    option_list = extract_options(field_list)
    return assemble_option_dict(option_list, options_spec)


def extract_options(field_list: nodes.field_list
                    ) -> list[tuple[str, str|None]]:
    """
    Return a list of option (name, value) pairs from field names & bodies.

    :Parameter:
        `field_list`: A flat field list, where each field name is a single
        word and each field body consists of a single paragraph only.

    :Exceptions:
        - `BadOptionError` for invalid fields.
        - `BadOptionDataError` for invalid option data (missing name,
          missing data, bad quotes, etc.).
    """
    option_list = []
    for field in field_list:
        if len(field[0].astext().split()) != 1:
            raise BadOptionError(
                'extension option field name may not contain multiple words')
        name = str(field[0].astext().lower())
        body = field[1]
        if len(body) == 0:
            data = None
        elif (len(body) > 1
              or not isinstance(body[0], nodes.paragraph)
              or len(body[0]) != 1
              or not isinstance(body[0][0], nodes.Text)):
            raise BadOptionDataError(
                  'extension option field body may contain\n'
                  'a single paragraph only (option "%s")' % name)
        else:
            data = body[0][0].astext()
        option_list.append((name, data))
    return option_list


def assemble_option_dict(option_list: list[tuple[str, str|None]],
                         options_spec: dict[str, Callable[object], Any],
                         ) -> dict[str, Any]:
    """
    Return a mapping of option names to values.

    :Parameters:
        - `option_list`: A list of (name, value) pairs (the output of
          `extract_options()`).
        - `options_spec`: Dictionary mapping known option names to a
          conversion function such as `int` or `float`.

    :Exceptions:
        - `KeyError` for unknown option names.
        - `DuplicateOptionError` for duplicate options.
        - `ValueError` for invalid option values (raised by conversion
           function).
        - `TypeError` for invalid option value types (raised by conversion
           function).
    """
    options = {}
    for name, value in option_list:
        convertor = options_spec[name]  # raises KeyError if unknown
        if convertor is None:
            raise KeyError(name)        # or if explicitly disabled
        if name in options:
            raise DuplicateOptionError('duplicate option "%s"' % name)
        try:
            options[name] = convertor(value)
        except (ValueError, TypeError) as detail:
            raise detail.__class__('(option: "%s"; value: %r)\n%s'
                                   % (name, value, ' '.join(detail.args)))
    return options


class NameValueError(DataError): pass


def decode_path(path: str|bytes|None) -> str:
    """
    Ensure `path` is Unicode. Return `str` instance.

    Decode file/path string in a failsafe manner if not already done.

    Deprecated. Will be removed in Docutils 1.0.
    """
    if isinstance(path, str):
        return path
    if path is None:
        return ''
    try:
        path = path.decode(sys.getfilesystemencoding(), 'strict')
    except AttributeError:
        raise ValueError('`path` value must be a String or ``None``, '
                         f'not {path!r}')
    except UnicodeDecodeError:
        try:
            path = path.decode('utf-8', 'strict')
        except UnicodeDecodeError:
            path = path.decode('ascii', 'replace')
    return path


def extract_name_value(line):
    """
    Return a list of (name, value) from a line of the form "name=value ...".

    :Exception:
        `NameValueError` for invalid input (missing name, missing data, bad
        quotes, etc.).
    """
    attlist = []
    while line:
        equals_index = line.find('=')
        if equals_index == -1:
            raise NameValueError('missing "="')
        attname = line[:equals_index].strip()
        if equals_index == 0 or not attname:
            raise NameValueError('missing attribute name before "="')
        line = line[equals_index+1:].lstrip()
        if not line:
            raise NameValueError(f'missing value after "{attname}="')
        if line[0] in '\'"':
            endquote_index = line.find(line[0], 1)
            if endquote_index == -1:
                raise NameValueError(
                      f'attribute "{attname}" missing end quote ({line[0]})')
            if (len(line) > endquote_index + 1
                and line[endquote_index + 1].strip()):
                raise NameValueError(f'attribute "{attname}" end quote '
                                     f'({line[0]}) not followed by whitespace')
            data = line[1:endquote_index]
            line = line[endquote_index+1:].lstrip()
        else:
            space_index = line.find(' ')
            if space_index == -1:
                data = line
                line = ''
            else:
                data = line[:space_index]
                line = line[space_index+1:].lstrip()
        attlist.append((attname.lower(), data))
    return attlist


def new_reporter(source_path: StrPath, settings: Values) -> Reporter:
    """
    Return a new Reporter object.

    :Parameters:
        `source` : string
            The path to or description of the source text of the document.
        `settings` : optparse.Values object
            Runtime settings.
    """
    reporter = Reporter(
        source_path, settings.report_level, settings.halt_level,
        stream=settings.warning_stream, debug=settings.debug,
        encoding=settings.error_encoding,
        error_handler=settings.error_encoding_error_handler)
    return reporter


def new_document(source_path: StrPath, settings: Values|None = None
                 ) -> nodes.document:
    """
    Return a new empty document object.

    :Parameters:
        `source_path` : str or pathlib.Path
            The path to or description of the source text of the document.
        `settings` : optparse.Values object
            Runtime settings.  If none are provided, a default core set will
            be used.  If you will use the document object with any Docutils
            components, you must provide their default settings as well.

            For example, if parsing rST, at least provide the rst-parser
            settings, obtainable as follows:

            Defaults for parser component::

                settings = docutils.frontend.get_default_settings(
                               docutils.parsers.rst.Parser)

            Defaults and configuration file customizations::

                settings = docutils.core.Publisher(
                    parser=docutils.parsers.rst.Parser).get_settings()

    """
    # Import at top of module would lead to circular dependency!
    from docutils import frontend
    if settings is None:
        settings = frontend.get_default_settings()
    reporter = new_reporter(source_path, settings)
    document = nodes.document(settings, reporter, source=source_path)
    document.note_source(source_path, -1)
    return document


def clean_rcs_keywords(
    paragraph: nodes.paragraph,
    keyword_substitutions: Sequence[tuple[re.Pattern[[str], str]]],
) -> None:
    if len(paragraph) == 1 and isinstance(paragraph[0], nodes.Text):
        textnode = paragraph[0]
        for pattern, substitution in keyword_substitutions:
            match = pattern.search(textnode)
            if match:
                paragraph[0] = nodes.Text(pattern.sub(substitution, textnode))
                return


def relative_path(source: StrPath|None, target: StrPath) -> str:
    """
    Build and return a path to `target`, relative to `source` (both files).

    The return value is a `str` suitable to be included in `source`
    as a reference to `target`.

    :Parameters:
        `source` : path-like object or None
            Path of a file in the start directory for the relative path
            (the file does not need to exist).
            The value ``None`` is replaced with "<cwd>/dummy_file".
        `target` : path-like object
            End point of the returned relative path.

    Differences to `os.path.relpath()`:

    * Inverse argument order.
    * `source` is assumed to be a FILE in the start directory (add a "dummy"
      file name to obtain the path relative from a directory)
      while `os.path.relpath()` expects a DIRECTORY as `start` argument.
    * Always use Posix path separator ("/") for the output.
    * Use `os.sep` for parsing the input
      (changing the value of `os.sep` is ignored by `os.relpath()`).
    * If there is no common prefix, return the absolute path to `target`.

    Differences to `pathlib.PurePath.relative_to(other)`:

    * pathlib offers an object oriented interface.
    * `source` expects path to a FILE while `other` expects a DIRECTORY.
    * `target` defaults to the cwd, no default value for `other`.
    * `relative_path()` always returns a path (relative or absolute),
      while `PurePath.relative_to()` raises a ValueError
      if `target` is not a subpath of `other` (no ".." inserted).
    """
    source_parts = os.path.abspath(source or type(target)('dummy_file')
                                   ).split(os.sep)
    target_parts = os.path.abspath(target).split(os.sep)
    # Check first 2 parts because '/dir'.split('/') == ['', 'dir']:
    if source_parts[:2] != target_parts[:2]:
        # Nothing in common between paths.
        # Return absolute path, using '/' for URLs:
        return '/'.join(target_parts)
    source_parts.reverse()
    target_parts.reverse()
    while (source_parts and target_parts
           and source_parts[-1] == target_parts[-1]):
        # Remove path components in common:
        source_parts.pop()
        target_parts.pop()
    target_parts.reverse()
    parts = ['..'] * (len(source_parts) - 1) + target_parts
    return '/'.join(parts)


def get_stylesheet_reference(settings: Values,
                             relative_to: StrPath|None = None
                             ) -> str:
    """
    Retrieve a stylesheet reference from the settings object.

    Deprecated. Will be removed in Docutils 1.0.
    Use get_stylesheet_list() instead to enable specification of multiple
    stylesheets as a comma-separated list.
    """
    warnings.warn('utils.get_stylesheet_reference()'
                  ' is obsoleted by utils.get_stylesheet_list()'
                  ' and will be removed in Docutils 2.0.',
                  DeprecationWarning, stacklevel=2)
    if settings.stylesheet_path:
        assert not settings.stylesheet, (
            'stylesheet and stylesheet_path are mutually exclusive.')
        if relative_to is None:
            relative_to = settings.output_path
        return relative_path(relative_to, settings.stylesheet_path)
    else:
        return settings.stylesheet


# Return 'stylesheet' or 'stylesheet_path' arguments as list.
#
# The original settings arguments are kept unchanged: you can test
# with e.g. ``if settings.stylesheet_path: ...``.
#
# Differences to the depracated `get_stylesheet_reference()`:
# * return value is a list
# * no re-writing of the path (and therefore no optional argument)
#   (if required, use ``utils.relative_path(source, target)``
#   in the calling script)
def get_stylesheet_list(settings: Values) -> list[str]:
    """Retrieve list of stylesheet references from the settings object."""
    assert not (settings.stylesheet and settings.stylesheet_path), (
            'stylesheet and stylesheet_path are mutually exclusive.')
    stylesheets = settings.stylesheet_path or settings.stylesheet or []
    # programmatically set default may be string with comma separated list:
    if not isinstance(stylesheets, list):
        stylesheets = [path.strip() for path in stylesheets.split(',')]
    if settings.stylesheet_path:
        # expand relative paths if found in stylesheet-dirs:
        stylesheets = [find_file_in_dirs(path, settings.stylesheet_dirs)
                       for path in stylesheets]
    return stylesheets


def find_file_in_dirs(path: StrPath, dirs: Iterable[StrPath]) -> str:
    """
    Search for `path` in the list of directories `dirs`.

    Return the first expansion that matches an existing file.
    """
    path = Path(path)
    if path.is_absolute():
        return path.as_posix()
    for d in dirs:
        f = Path(d).expanduser() / path
        if f.exists():
            return f.as_posix()
    return path.as_posix()


def get_trim_footnote_ref_space(settings: Values) -> bool:
    """
    Return whether or not to trim footnote space.

    If trim_footnote_reference_space is not None, return it.

    If trim_footnote_reference_space is None, return False unless the
    footnote reference style is 'superscript'.
    """
    if settings.setdefault('trim_footnote_reference_space', None) is None:
        return getattr(settings, 'footnote_references', None) == 'superscript'
    else:
        return settings.trim_footnote_reference_space


def get_source_line(node) -> tuple[StrPath|None, int|None]:
    """
    Return the "source" and "line" attributes from the `node` given or from
    its closest ancestor.
    """
    while node:
        if node.source or node.line:
            return node.source, node.line
        node = node.parent
    return None, None


def escape2null(text: str) -> str:
    """Return a string with escape-backslashes converted to nulls."""
    parts = []
    start = 0
    while True:
        bs_index = text.find('\\', start)
        if bs_index == -1:
            parts.append(text[start:])
            return ''.join(parts)
        parts.extend((text[start:bs_index],
                      '\x00' + text[bs_index + 1:bs_index + 2]))
        start = bs_index + 2  # skip character after escape


def split_escaped_whitespace(text: str) -> list[str]:
    """
    Split `text` on escaped whitespace (null+space or null+newline).
    Return a list of strings.
    """
    strings = text.split('\x00 ')
    strings = [string.split('\x00\n') for string in strings]
    # flatten list of lists of strings to list of strings:
    return list(itertools.chain(*strings))


def strip_combining_chars(text: str) -> str:
    return ''.join(c for c in text if not unicodedata.combining(c))


def find_combining_chars(text: str) -> list[int]:
    """Return indices of all combining chars in  Unicode string `text`.

    >>> from docutils.utils import find_combining_chars
    >>> find_combining_chars('A t̆ab̆lĕ')
    [3, 6, 9]

    """
    return [i for i, c in enumerate(text) if unicodedata.combining(c)]


def column_indices(text: str) -> list[int]:
    """Indices of Unicode string `text` when skipping combining characters.

    >>> from docutils.utils import column_indices
    >>> column_indices('A t̆ab̆lĕ')
    [0, 1, 2, 4, 5, 7, 8]

    """
    # TODO: account for asian wide chars here instead of using dummy
    # replacements in the tableparser?
    return [i for i, c in enumerate(text) if not unicodedata.combining(c)]


east_asian_widths = {'W': 2,   # Wide
                     'F': 2,   # Full-width (wide)
                     'Na': 1,  # Narrow
                     'H': 1,   # Half-width (narrow)
                     'N': 1,   # Neutral (not East Asian, treated as narrow)
                     'A': 1,   # Ambiguous (s/b wide in East Asian context,
                     }         # narrow otherwise, but that doesn't work)
"""Mapping of result codes from `unicodedata.east_asian_widt()` to character
column widths."""


def column_width(text: str) -> int:
    """Return the column width of text.

    Correct ``len(text)`` for wide East Asian and combining Unicode chars.
    """
    width = sum(east_asian_widths[unicodedata.east_asian_width(c)]
                for c in text)
    # correction for combining chars:
    width -= len(find_combining_chars(text))
    return width


def uniq(L: list) -> list:
    r = []
    for item in L:
        if item not in r:
            r.append(item)
    return r


def normalize_language_tag(tag: str) -> list[str]:
    """Return a list of normalized combinations for a `BCP 47` language tag.

    Example:

    >>> from docutils.utils import normalize_language_tag
    >>> normalize_language_tag('de_AT-1901')
    ['de-at-1901', 'de-at', 'de-1901', 'de']
    >>> normalize_language_tag('de-CH-x_altquot')
    ['de-ch-x-altquot', 'de-ch', 'de-x-altquot', 'de']

    """
    # normalize:
    tag = tag.lower().replace('-', '_')
    # split (except singletons, which mark the following tag as non-standard):
    tag = re.sub(r'_([a-zA-Z0-9])_', r'_\1-', tag)
    subtags = list(tag.split('_'))
    base_tag = (subtags.pop(0),)
    # find all combinations of subtags
    taglist = ['-'.join(base_tag + tags)
               for n in range(len(subtags), 0, -1)
               for tags in itertools.combinations(subtags, n)
               ]
    taglist += base_tag
    return taglist


def xml_declaration(encoding: str|Literal['unicode']|None = None) -> str:
    """Return an XML text declaration.

    Include an encoding declaration, if `encoding`
    is not 'unicode', '', or None.
    """
    if encoding and encoding.lower() != 'unicode':
        encoding_declaration = f' encoding="{encoding}"'
    else:
        encoding_declaration = ''
    return f'<?xml version="1.0"{encoding_declaration}?>\n'


class DependencyList:

    """
    List of dependencies, with file recording support.

    Note that the output file is not automatically closed.  You have
    to explicitly call the close() method.
    """

    def __init__(self,
                 output_file: Literal['-'] | StrPath | None = None,
                 dependencies: Iterable[StrPath] = ()
                 ) -> None:
        """
        Initialize the dependency list, automatically setting the
        output file to `output_file` (see `set_output()`) and adding
        all supplied dependencies.

        If output_file is None, no file output is done when calling add().
        """
        self.set_output(output_file)
        self.add(*dependencies)

    def set_output(self, output_file: Literal['-']|StrPath|None) -> None:
        """
        Set the output file and clear the list of already added
        dependencies.

        The specified file is immediately overwritten.

        If `output_file` is '-', the output will be written to stdout.
        The empty string or None stop output.
        """
        if output_file == '-':
            self.file = sys.stdout
        elif output_file:
            self.file = open(output_file, 'w', encoding='utf-8')
        else:
            self.file = None
        self.list = []

    def add(self, *paths: StrPath) -> None:
        """
        Append `path` to `self.list` unless it is already there.

        Also append to `self.file` unless it is already there
        or `self.file is `None`.
        """
        for path in paths:
            if isinstance(path, PurePath):
                path = path.as_posix()  # use '/' as separator
            if path not in self.list:
                self.list.append(path)
                if self.file is not None:
                    self.file.write(path+'\n')

    def close(self) -> None:
        """
        Close the output file.
        """
        if self.file is not sys.stdout:
            self.file.close()
        self.file = None

    def __repr__(self) -> str:
        try:
            output_file = self.file.name
        except AttributeError:
            output_file = None
        return '%s(%r, %s)' % (self.__class__.__name__, output_file, self.list)
