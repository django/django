"""
    babel.messages.pofile
    ~~~~~~~~~~~~~~~~~~~~~

    Reading and writing of files in the ``gettext`` PO (portable object)
    format.

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

from babel.core import Locale
from babel.messages.catalog import Catalog, Message
from babel.util import _cmp, wraptext

if TYPE_CHECKING:
    from typing import IO, AnyStr

    from _typeshed import SupportsWrite
    from typing_extensions import Literal


def unescape(string: str) -> str:
    r"""Reverse `escape` the given string.

    >>> print(unescape('"Say:\\n  \\"hello, world!\\"\\n"'))
    Say:
      "hello, world!"
    <BLANKLINE>

    :param string: the string to unescape
    """
    def replace_escapes(match):
        m = match.group(1)
        if m == 'n':
            return '\n'
        elif m == 't':
            return '\t'
        elif m == 'r':
            return '\r'
        # m is \ or "
        return m
    return re.compile(r'\\([\\trn"])').sub(replace_escapes, string[1:-1])


def denormalize(string: str) -> str:
    r"""Reverse the normalization done by the `normalize` function.

    >>> print(denormalize(r'''""
    ... "Say:\n"
    ... "  \"hello, world!\"\n"'''))
    Say:
      "hello, world!"
    <BLANKLINE>

    >>> print(denormalize(r'''""
    ... "Say:\n"
    ... "  \"Lorem ipsum dolor sit "
    ... "amet, consectetur adipisicing"
    ... " elit, \"\n"'''))
    Say:
      "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    <BLANKLINE>

    :param string: the string to denormalize
    """
    if '\n' in string:
        escaped_lines = string.splitlines()
        if string.startswith('""'):
            escaped_lines = escaped_lines[1:]
        lines = map(unescape, escaped_lines)
        return ''.join(lines)
    else:
        return unescape(string)


class PoFileError(Exception):
    """Exception thrown by PoParser when an invalid po file is encountered."""

    def __init__(self, message: str, catalog: Catalog, line: str, lineno: int) -> None:
        super().__init__(f'{message} on {lineno}')
        self.catalog = catalog
        self.line = line
        self.lineno = lineno


class _NormalizedString:

    def __init__(self, *args: str) -> None:
        self._strs: list[str] = []
        for arg in args:
            self.append(arg)

    def append(self, s: str) -> None:
        self._strs.append(s.strip())

    def denormalize(self) -> str:
        return ''.join(map(unescape, self._strs))

    def __bool__(self) -> bool:
        return bool(self._strs)

    def __repr__(self) -> str:
        return os.linesep.join(self._strs)

    def __cmp__(self, other: object) -> int:
        if not other:
            return 1

        return _cmp(str(self), str(other))

    def __gt__(self, other: object) -> bool:
        return self.__cmp__(other) > 0

    def __lt__(self, other: object) -> bool:
        return self.__cmp__(other) < 0

    def __ge__(self, other: object) -> bool:
        return self.__cmp__(other) >= 0

    def __le__(self, other: object) -> bool:
        return self.__cmp__(other) <= 0

    def __eq__(self, other: object) -> bool:
        return self.__cmp__(other) == 0

    def __ne__(self, other: object) -> bool:
        return self.__cmp__(other) != 0


class PoFileParser:
    """Support class to  read messages from a ``gettext`` PO (portable object) file
    and add them to a `Catalog`

    See `read_po` for simple cases.
    """

    _keywords = [
        'msgid',
        'msgstr',
        'msgctxt',
        'msgid_plural',
    ]

    def __init__(self, catalog: Catalog, ignore_obsolete: bool = False, abort_invalid: bool = False) -> None:
        self.catalog = catalog
        self.ignore_obsolete = ignore_obsolete
        self.counter = 0
        self.offset = 0
        self.abort_invalid = abort_invalid
        self._reset_message_state()

    def _reset_message_state(self) -> None:
        self.messages = []
        self.translations = []
        self.locations = []
        self.flags = []
        self.user_comments = []
        self.auto_comments = []
        self.context = None
        self.obsolete = False
        self.in_msgid = False
        self.in_msgstr = False
        self.in_msgctxt = False

    def _add_message(self) -> None:
        """
        Add a message to the catalog based on the current parser state and
        clear the state ready to process the next message.
        """
        self.translations.sort()
        if len(self.messages) > 1:
            msgid = tuple(m.denormalize() for m in self.messages)
        else:
            msgid = self.messages[0].denormalize()
        if isinstance(msgid, (list, tuple)):
            string = ['' for _ in range(self.catalog.num_plurals)]
            for idx, translation in self.translations:
                if idx >= self.catalog.num_plurals:
                    self._invalid_pofile("", self.offset, "msg has more translations than num_plurals of catalog")
                    continue
                string[idx] = translation.denormalize()
            string = tuple(string)
        else:
            string = self.translations[0][1].denormalize()
        msgctxt = self.context.denormalize() if self.context else None
        message = Message(msgid, string, list(self.locations), set(self.flags),
                          self.auto_comments, self.user_comments, lineno=self.offset + 1,
                          context=msgctxt)
        if self.obsolete:
            if not self.ignore_obsolete:
                self.catalog.obsolete[msgid] = message
        else:
            self.catalog[msgid] = message
        self.counter += 1
        self._reset_message_state()

    def _finish_current_message(self) -> None:
        if self.messages:
            self._add_message()

    def _process_message_line(self, lineno, line, obsolete=False) -> None:
        if line.startswith('"'):
            self._process_string_continuation_line(line, lineno)
        else:
            self._process_keyword_line(lineno, line, obsolete)

    def _process_keyword_line(self, lineno, line, obsolete=False) -> None:

        for keyword in self._keywords:
            try:
                if line.startswith(keyword) and line[len(keyword)] in [' ', '[']:
                    arg = line[len(keyword):]
                    break
            except IndexError:
                self._invalid_pofile(line, lineno, "Keyword must be followed by a string")
        else:
            self._invalid_pofile(line, lineno, "Start of line didn't match any expected keyword.")
            return

        if keyword in ['msgid', 'msgctxt']:
            self._finish_current_message()

        self.obsolete = obsolete

        # The line that has the msgid is stored as the offset of the msg
        # should this be the msgctxt if it has one?
        if keyword == 'msgid':
            self.offset = lineno

        if keyword in ['msgid', 'msgid_plural']:
            self.in_msgctxt = False
            self.in_msgid = True
            self.messages.append(_NormalizedString(arg))

        elif keyword == 'msgstr':
            self.in_msgid = False
            self.in_msgstr = True
            if arg.startswith('['):
                idx, msg = arg[1:].split(']', 1)
                self.translations.append([int(idx), _NormalizedString(msg)])
            else:
                self.translations.append([0, _NormalizedString(arg)])

        elif keyword == 'msgctxt':
            self.in_msgctxt = True
            self.context = _NormalizedString(arg)

    def _process_string_continuation_line(self, line, lineno) -> None:
        if self.in_msgid:
            s = self.messages[-1]
        elif self.in_msgstr:
            s = self.translations[-1][1]
        elif self.in_msgctxt:
            s = self.context
        else:
            self._invalid_pofile(line, lineno, "Got line starting with \" but not in msgid, msgstr or msgctxt")
            return
        s.append(line)

    def _process_comment(self, line) -> None:

        self._finish_current_message()

        if line[1:].startswith(':'):
            for location in line[2:].lstrip().split():
                pos = location.rfind(':')
                if pos >= 0:
                    try:
                        lineno = int(location[pos + 1:])
                    except ValueError:
                        continue
                    self.locations.append((location[:pos], lineno))
                else:
                    self.locations.append((location, None))
        elif line[1:].startswith(','):
            for flag in line[2:].lstrip().split(','):
                self.flags.append(flag.strip())
        elif line[1:].startswith('.'):
            # These are called auto-comments
            comment = line[2:].strip()
            if comment:  # Just check that we're not adding empty comments
                self.auto_comments.append(comment)
        else:
            # These are called user comments
            self.user_comments.append(line[1:].strip())

    def parse(self, fileobj: IO[AnyStr]) -> None:
        """
        Reads from the file-like object `fileobj` and adds any po file
        units found in it to the `Catalog` supplied to the constructor.
        """

        for lineno, line in enumerate(fileobj):
            line = line.strip()
            if not isinstance(line, str):
                line = line.decode(self.catalog.charset)
            if not line:
                continue
            if line.startswith('#'):
                if line[1:].startswith('~'):
                    self._process_message_line(lineno, line[2:].lstrip(), obsolete=True)
                else:
                    self._process_comment(line)
            else:
                self._process_message_line(lineno, line)

        self._finish_current_message()

        # No actual messages found, but there was some info in comments, from which
        # we'll construct an empty header message
        if not self.counter and (self.flags or self.user_comments or self.auto_comments):
            self.messages.append(_NormalizedString('""'))
            self.translations.append([0, _NormalizedString('""')])
            self._add_message()

    def _invalid_pofile(self, line, lineno, msg) -> None:
        assert isinstance(line, str)
        if self.abort_invalid:
            raise PoFileError(msg, self.catalog, line, lineno)
        print("WARNING:", msg)
        print(f"WARNING: Problem on line {lineno + 1}: {line!r}")


def read_po(
    fileobj: IO[AnyStr],
    locale: str | Locale | None = None,
    domain: str | None = None,
    ignore_obsolete: bool = False,
    charset: str | None = None,
    abort_invalid: bool = False,
) -> Catalog:
    """Read messages from a ``gettext`` PO (portable object) file from the given
    file-like object and return a `Catalog`.

    >>> from datetime import datetime
    >>> from io import StringIO
    >>> buf = StringIO('''
    ... #: main.py:1
    ... #, fuzzy, python-format
    ... msgid "foo %(name)s"
    ... msgstr "quux %(name)s"
    ...
    ... # A user comment
    ... #. An auto comment
    ... #: main.py:3
    ... msgid "bar"
    ... msgid_plural "baz"
    ... msgstr[0] "bar"
    ... msgstr[1] "baaz"
    ... ''')
    >>> catalog = read_po(buf)
    >>> catalog.revision_date = datetime(2007, 4, 1)

    >>> for message in catalog:
    ...     if message.id:
    ...         print((message.id, message.string))
    ...         print(' ', (message.locations, sorted(list(message.flags))))
    ...         print(' ', (message.user_comments, message.auto_comments))
    (u'foo %(name)s', u'quux %(name)s')
      ([(u'main.py', 1)], [u'fuzzy', u'python-format'])
      ([], [])
    ((u'bar', u'baz'), (u'bar', u'baaz'))
      ([(u'main.py', 3)], [])
      ([u'A user comment'], [u'An auto comment'])

    .. versionadded:: 1.0
       Added support for explicit charset argument.

    :param fileobj: the file-like object to read the PO file from
    :param locale: the locale identifier or `Locale` object, or `None`
                   if the catalog is not bound to a locale (which basically
                   means it's a template)
    :param domain: the message domain
    :param ignore_obsolete: whether to ignore obsolete messages in the input
    :param charset: the character set of the catalog.
    :param abort_invalid: abort read if po file is invalid
    """
    catalog = Catalog(locale=locale, domain=domain, charset=charset)
    parser = PoFileParser(catalog, ignore_obsolete, abort_invalid=abort_invalid)
    parser.parse(fileobj)
    return catalog


WORD_SEP = re.compile('('
                      r'\s+|'                                 # any whitespace
                      r'[^\s\w]*\w+[a-zA-Z]-(?=\w+[a-zA-Z])|'  # hyphenated words
                      r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w)'   # em-dash
                      ')')


def escape(string: str) -> str:
    r"""Escape the given string so that it can be included in double-quoted
    strings in ``PO`` files.

    >>> escape('''Say:
    ...   "hello, world!"
    ... ''')
    '"Say:\\n  \\"hello, world!\\"\\n"'

    :param string: the string to escape
    """
    return '"%s"' % string.replace('\\', '\\\\') \
                          .replace('\t', '\\t') \
                          .replace('\r', '\\r') \
                          .replace('\n', '\\n') \
                          .replace('\"', '\\"')


def normalize(string: str, prefix: str = '', width: int = 76) -> str:
    r"""Convert a string into a format that is appropriate for .po files.

    >>> print(normalize('''Say:
    ...   "hello, world!"
    ... ''', width=None))
    ""
    "Say:\n"
    "  \"hello, world!\"\n"

    >>> print(normalize('''Say:
    ...   "Lorem ipsum dolor sit amet, consectetur adipisicing elit, "
    ... ''', width=32))
    ""
    "Say:\n"
    "  \"Lorem ipsum dolor sit "
    "amet, consectetur adipisicing"
    " elit, \"\n"

    :param string: the string to normalize
    :param prefix: a string that should be prepended to every line
    :param width: the maximum line width; use `None`, 0, or a negative number
                  to completely disable line wrapping
    """
    if width and width > 0:
        prefixlen = len(prefix)
        lines = []
        for line in string.splitlines(True):
            if len(escape(line)) + prefixlen > width:
                chunks = WORD_SEP.split(line)
                chunks.reverse()
                while chunks:
                    buf = []
                    size = 2
                    while chunks:
                        length = len(escape(chunks[-1])) - 2 + prefixlen
                        if size + length < width:
                            buf.append(chunks.pop())
                            size += length
                        else:
                            if not buf:
                                # handle long chunks by putting them on a
                                # separate line
                                buf.append(chunks.pop())
                            break
                    lines.append(''.join(buf))
            else:
                lines.append(line)
    else:
        lines = string.splitlines(True)

    if len(lines) <= 1:
        return escape(string)

    # Remove empty trailing line
    if lines and not lines[-1]:
        del lines[-1]
        lines[-1] += '\n'
    return '""\n' + '\n'.join([(prefix + escape(line)) for line in lines])


def write_po(
    fileobj: SupportsWrite[bytes],
    catalog: Catalog,
    width: int = 76,
    no_location: bool = False,
    omit_header: bool = False,
    sort_output: bool = False,
    sort_by_file: bool = False,
    ignore_obsolete: bool = False,
    include_previous: bool = False,
    include_lineno: bool = True,
) -> None:
    r"""Write a ``gettext`` PO (portable object) template file for a given
    message catalog to the provided file-like object.

    >>> catalog = Catalog()
    >>> catalog.add(u'foo %(name)s', locations=[('main.py', 1)],
    ...             flags=('fuzzy',))
    <Message...>
    >>> catalog.add((u'bar', u'baz'), locations=[('main.py', 3)])
    <Message...>
    >>> from io import BytesIO
    >>> buf = BytesIO()
    >>> write_po(buf, catalog, omit_header=True)
    >>> print(buf.getvalue().decode("utf8"))
    #: main.py:1
    #, fuzzy, python-format
    msgid "foo %(name)s"
    msgstr ""
    <BLANKLINE>
    #: main.py:3
    msgid "bar"
    msgid_plural "baz"
    msgstr[0] ""
    msgstr[1] ""
    <BLANKLINE>
    <BLANKLINE>

    :param fileobj: the file-like object to write to
    :param catalog: the `Catalog` instance
    :param width: the maximum line width for the generated output; use `None`,
                  0, or a negative number to completely disable line wrapping
    :param no_location: do not emit a location comment for every message
    :param omit_header: do not include the ``msgid ""`` entry at the top of the
                        output
    :param sort_output: whether to sort the messages in the output by msgid
    :param sort_by_file: whether to sort the messages in the output by their
                         locations
    :param ignore_obsolete: whether to ignore obsolete messages and not include
                            them in the output; by default they are included as
                            comments
    :param include_previous: include the old msgid as a comment when
                             updating the catalog
    :param include_lineno: include line number in the location comment
    """
    def _normalize(key, prefix=''):
        return normalize(key, prefix=prefix, width=width)

    def _write(text):
        if isinstance(text, str):
            text = text.encode(catalog.charset, 'backslashreplace')
        fileobj.write(text)

    def _write_comment(comment, prefix=''):
        # xgettext always wraps comments even if --no-wrap is passed;
        # provide the same behaviour
        _width = width if width and width > 0 else 76
        for line in wraptext(comment, _width):
            _write(f"#{prefix} {line.strip()}\n")

    def _write_message(message, prefix=''):
        if isinstance(message.id, (list, tuple)):
            if message.context:
                _write(f"{prefix}msgctxt {_normalize(message.context, prefix)}\n")
            _write(f"{prefix}msgid {_normalize(message.id[0], prefix)}\n")
            _write(f"{prefix}msgid_plural {_normalize(message.id[1], prefix)}\n")

            for idx in range(catalog.num_plurals):
                try:
                    string = message.string[idx]
                except IndexError:
                    string = ''
                _write(f"{prefix}msgstr[{idx:d}] {_normalize(string, prefix)}\n")
        else:
            if message.context:
                _write(f"{prefix}msgctxt {_normalize(message.context, prefix)}\n")
            _write(f"{prefix}msgid {_normalize(message.id, prefix)}\n")
            _write(f"{prefix}msgstr {_normalize(message.string or '', prefix)}\n")

    sort_by = None
    if sort_output:
        sort_by = "message"
    elif sort_by_file:
        sort_by = "location"

    for message in _sort_messages(catalog, sort_by=sort_by):
        if not message.id:  # This is the header "message"
            if omit_header:
                continue
            comment_header = catalog.header_comment
            if width and width > 0:
                lines = []
                for line in comment_header.splitlines():
                    lines += wraptext(line, width=width,
                                      subsequent_indent='# ')
                comment_header = '\n'.join(lines)
            _write(f"{comment_header}\n")

        for comment in message.user_comments:
            _write_comment(comment)
        for comment in message.auto_comments:
            _write_comment(comment, prefix='.')

        if not no_location:
            locs = []

            # sort locations by filename and lineno.
            # if there's no <int> as lineno, use `-1`.
            # if no sorting possible, leave unsorted.
            # (see issue #606)
            try:
                locations = sorted(message.locations,
                                   key=lambda x: (x[0], isinstance(x[1], int) and x[1] or -1))
            except TypeError:  # e.g. "TypeError: unorderable types: NoneType() < int()"
                locations = message.locations

            for filename, lineno in locations:
                location = filename.replace(os.sep, '/')
                if lineno and include_lineno:
                    location = f"{location}:{lineno:d}"
                if location not in locs:
                    locs.append(location)
            _write_comment(' '.join(locs), prefix=':')
        if message.flags:
            _write(f"#{', '.join(['', *sorted(message.flags)])}\n")

        if message.previous_id and include_previous:
            _write_comment(
                f'msgid {_normalize(message.previous_id[0])}',
                prefix='|',
            )
            if len(message.previous_id) > 1:
                _write_comment('msgid_plural %s' % _normalize(
                    message.previous_id[1],
                ), prefix='|')

        _write_message(message)
        _write('\n')

    if not ignore_obsolete:
        for message in _sort_messages(
            catalog.obsolete.values(),
            sort_by=sort_by,
        ):
            for comment in message.user_comments:
                _write_comment(comment)
            _write_message(message, prefix='#~ ')
            _write('\n')


def _sort_messages(messages: Iterable[Message], sort_by: Literal["message", "location"]) -> list[Message]:
    """
    Sort the given message iterable by the given criteria.

    Always returns a list.

    :param messages: An iterable of Messages.
    :param sort_by: Sort by which criteria? Options are `message` and `location`.
    :return: list[Message]
    """
    messages = list(messages)
    if sort_by == "message":
        messages.sort()
    elif sort_by == "location":
        messages.sort(key=lambda m: m.locations)
    return messages
