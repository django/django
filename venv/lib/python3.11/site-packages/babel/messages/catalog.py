"""
    babel.messages.catalog
    ~~~~~~~~~~~~~~~~~~~~~~

    Data structures for message catalogs.

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import annotations

import datetime
import re
from collections import OrderedDict
from collections.abc import Iterable, Iterator
from copy import copy
from difflib import SequenceMatcher
from email import message_from_string
from heapq import nlargest
from typing import TYPE_CHECKING

from babel import __version__ as VERSION
from babel.core import Locale, UnknownLocaleError
from babel.dates import format_datetime
from babel.messages.plurals import get_plural
from babel.util import LOCALTZ, FixedOffsetTimezone, _cmp, distinct

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    _MessageID: TypeAlias = str | tuple[str, ...] | list[str]

__all__ = ['Message', 'Catalog', 'TranslationError']

def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    """A modified version of ``difflib.get_close_matches``.

    It just passes ``autojunk=False`` to the ``SequenceMatcher``, to work
    around https://github.com/python/cpython/issues/90825.
    """
    if not n > 0:  # pragma: no cover
        raise ValueError(f"n must be > 0: {n!r}")
    if not 0.0 <= cutoff <= 1.0:  # pragma: no cover
        raise ValueError(f"cutoff must be in [0.0, 1.0]: {cutoff!r}")
    result = []
    s = SequenceMatcher(autojunk=False) # only line changed from difflib.py
    s.set_seq2(word)
    for x in possibilities:
        s.set_seq1(x)
        if s.real_quick_ratio() >= cutoff and \
           s.quick_ratio() >= cutoff and \
           s.ratio() >= cutoff:
            result.append((s.ratio(), x))

    # Move the best scorers to head of list
    result = nlargest(n, result)
    # Strip scores for the best n matches
    return [x for score, x in result]


PYTHON_FORMAT = re.compile(r'''
    \%
        (?:\(([\w]*)\))?
        (
            [-#0\ +]?(?:\*|[\d]+)?
            (?:\.(?:\*|[\d]+))?
            [hlL]?
        )
        ([diouxXeEfFgGcrs%])
''', re.VERBOSE)


def _parse_datetime_header(value: str) -> datetime.datetime:
    match = re.match(r'^(?P<datetime>.*?)(?P<tzoffset>[+-]\d{4})?$', value)

    dt = datetime.datetime.strptime(match.group('datetime'), '%Y-%m-%d %H:%M')

    # Separate the offset into a sign component, hours, and # minutes
    tzoffset = match.group('tzoffset')
    if tzoffset is not None:
        plus_minus_s, rest = tzoffset[0], tzoffset[1:]
        hours_offset_s, mins_offset_s = rest[:2], rest[2:]

        # Make them all integers
        plus_minus = int(f"{plus_minus_s}1")
        hours_offset = int(hours_offset_s)
        mins_offset = int(mins_offset_s)

        # Calculate net offset
        net_mins_offset = hours_offset * 60
        net_mins_offset += mins_offset
        net_mins_offset *= plus_minus

        # Create an offset object
        tzoffset = FixedOffsetTimezone(net_mins_offset)

        # Store the offset in a datetime object
        dt = dt.replace(tzinfo=tzoffset)

    return dt


class Message:
    """Representation of a single message in a catalog."""

    def __init__(
        self,
        id: _MessageID,
        string: _MessageID | None = '',
        locations: Iterable[tuple[str, int]] = (),
        flags: Iterable[str] = (),
        auto_comments: Iterable[str] = (),
        user_comments: Iterable[str] = (),
        previous_id: _MessageID = (),
        lineno: int | None = None,
        context: str | None = None,
    ) -> None:
        """Create the message object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filename, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments for the message
        :param user_comments: a sequence of user comments for the message
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        :param context: the message context
        """
        self.id = id
        if not string and self.pluralizable:
            string = ('', '')
        self.string = string
        self.locations = list(distinct(locations))
        self.flags = set(flags)
        if id and self.python_format:
            self.flags.add('python-format')
        else:
            self.flags.discard('python-format')
        self.auto_comments = list(distinct(auto_comments))
        self.user_comments = list(distinct(user_comments))
        if isinstance(previous_id, str):
            self.previous_id = [previous_id]
        else:
            self.previous_id = list(previous_id)
        self.lineno = lineno
        self.context = context

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.id!r} (flags: {list(self.flags)!r})>"

    def __cmp__(self, other: object) -> int:
        """Compare Messages, taking into account plural ids"""
        def values_to_compare(obj):
            if isinstance(obj, Message) and obj.pluralizable:
                return obj.id[0], obj.context or ''
            return obj.id, obj.context or ''
        return _cmp(values_to_compare(self), values_to_compare(other))

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

    def is_identical(self, other: Message) -> bool:
        """Checks whether messages are identical, taking into account all
        properties.
        """
        assert isinstance(other, Message)
        return self.__dict__ == other.__dict__

    def clone(self) -> Message:
        return Message(*map(copy, (self.id, self.string, self.locations,
                                   self.flags, self.auto_comments,
                                   self.user_comments, self.previous_id,
                                   self.lineno, self.context)))

    def check(self, catalog: Catalog | None = None) -> list[TranslationError]:
        """Run various validation checks on the message.  Some validations
        are only performed if the catalog is provided.  This method returns
        a sequence of `TranslationError` objects.

        :rtype: ``iterator``
        :param catalog: A catalog instance that is passed to the checkers
        :see: `Catalog.check` for a way to perform checks for all messages
              in a catalog.
        """
        from babel.messages.checkers import checkers
        errors: list[TranslationError] = []
        for checker in checkers:
            try:
                checker(catalog, self)
            except TranslationError as e:
                errors.append(e)
        return errors

    @property
    def fuzzy(self) -> bool:
        """Whether the translation is fuzzy.

        >>> Message('foo').fuzzy
        False
        >>> msg = Message('foo', 'foo', flags=['fuzzy'])
        >>> msg.fuzzy
        True
        >>> msg
        <Message 'foo' (flags: ['fuzzy'])>

        :type:  `bool`"""
        return 'fuzzy' in self.flags

    @property
    def pluralizable(self) -> bool:
        """Whether the message is plurizable.

        >>> Message('foo').pluralizable
        False
        >>> Message(('foo', 'bar')).pluralizable
        True

        :type:  `bool`"""
        return isinstance(self.id, (list, tuple))

    @property
    def python_format(self) -> bool:
        """Whether the message contains Python-style parameters.

        >>> Message('foo %(name)s bar').python_format
        True
        >>> Message(('foo %(name)s', 'foo %(name)s')).python_format
        True

        :type:  `bool`"""
        ids = self.id
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        return any(PYTHON_FORMAT.search(id) for id in ids)


class TranslationError(Exception):
    """Exception thrown by translation checkers when invalid message
    translations are encountered."""


DEFAULT_HEADER = """\
# Translations template for PROJECT.
# Copyright (C) YEAR ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#"""


def parse_separated_header(value: str) -> dict[str, str]:
    # Adapted from https://peps.python.org/pep-0594/#cgi
    from email.message import Message
    m = Message()
    m['content-type'] = value
    return dict(m.get_params())


class Catalog:
    """Representation of a message catalog."""

    def __init__(
        self,
        locale: str | Locale | None = None,
        domain: str | None = None,
        header_comment: str | None = DEFAULT_HEADER,
        project: str | None = None,
        version: str | None = None,
        copyright_holder: str | None = None,
        msgid_bugs_address: str | None = None,
        creation_date: datetime.datetime | str | None = None,
        revision_date: datetime.datetime | datetime.time | float | str | None = None,
        last_translator: str | None = None,
        language_team: str | None = None,
        charset: str | None = None,
        fuzzy: bool = True,
    ) -> None:
        """Initialize the catalog object.

        :param locale: the locale identifier or `Locale` object, or `None`
                       if the catalog is not bound to a locale (which basically
                       means it's a template)
        :param domain: the message domain
        :param header_comment: the header comment as string, or `None` for the
                               default header
        :param project: the project's name
        :param version: the project's version
        :param copyright_holder: the copyright holder of the catalog
        :param msgid_bugs_address: the email address or URL to submit bug
                                   reports to
        :param creation_date: the date the catalog was created
        :param revision_date: the date the catalog was revised
        :param last_translator: the name and email of the last translator
        :param language_team: the name and email of the language team
        :param charset: the encoding to use in the output (defaults to utf-8)
        :param fuzzy: the fuzzy bit on the catalog header
        """
        self.domain = domain
        self.locale = locale
        self._header_comment = header_comment
        self._messages: OrderedDict[str | tuple[str, str], Message] = OrderedDict()

        self.project = project or 'PROJECT'
        self.version = version or 'VERSION'
        self.copyright_holder = copyright_holder or 'ORGANIZATION'
        self.msgid_bugs_address = msgid_bugs_address or 'EMAIL@ADDRESS'

        self.last_translator = last_translator or 'FULL NAME <EMAIL@ADDRESS>'
        """Name and email address of the last translator."""
        self.language_team = language_team or 'LANGUAGE <LL@li.org>'
        """Name and email address of the language team."""

        self.charset = charset or 'utf-8'

        if creation_date is None:
            creation_date = datetime.datetime.now(LOCALTZ)
        elif isinstance(creation_date, datetime.datetime) and not creation_date.tzinfo:
            creation_date = creation_date.replace(tzinfo=LOCALTZ)
        self.creation_date = creation_date
        if revision_date is None:
            revision_date = 'YEAR-MO-DA HO:MI+ZONE'
        elif isinstance(revision_date, datetime.datetime) and not revision_date.tzinfo:
            revision_date = revision_date.replace(tzinfo=LOCALTZ)
        self.revision_date = revision_date
        self.fuzzy = fuzzy

        # Dictionary of obsolete messages
        self.obsolete: OrderedDict[str | tuple[str, str], Message] = OrderedDict()
        self._num_plurals = None
        self._plural_expr = None

    def _set_locale(self, locale: Locale | str | None) -> None:
        if locale is None:
            self._locale_identifier = None
            self._locale = None
            return

        if isinstance(locale, Locale):
            self._locale_identifier = str(locale)
            self._locale = locale
            return

        if isinstance(locale, str):
            self._locale_identifier = str(locale)
            try:
                self._locale = Locale.parse(locale)
            except UnknownLocaleError:
                self._locale = None
            return

        raise TypeError(f"`locale` must be a Locale, a locale identifier string, or None; got {locale!r}")

    def _get_locale(self) -> Locale | None:
        return self._locale

    def _get_locale_identifier(self) -> str | None:
        return self._locale_identifier

    locale = property(_get_locale, _set_locale)
    locale_identifier = property(_get_locale_identifier)

    def _get_header_comment(self) -> str:
        comment = self._header_comment
        year = datetime.datetime.now(LOCALTZ).strftime('%Y')
        if hasattr(self.revision_date, 'strftime'):
            year = self.revision_date.strftime('%Y')
        comment = comment.replace('PROJECT', self.project) \
                         .replace('VERSION', self.version) \
                         .replace('YEAR', year) \
                         .replace('ORGANIZATION', self.copyright_holder)
        locale_name = (self.locale.english_name if self.locale else self.locale_identifier)
        if locale_name:
            comment = comment.replace("Translations template", f"{locale_name} translations")
        return comment

    def _set_header_comment(self, string: str | None) -> None:
        self._header_comment = string

    header_comment = property(_get_header_comment, _set_header_comment, doc="""\
    The header comment for the catalog.

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> print(catalog.header_comment) #doctest: +ELLIPSIS
    # Translations template for Foobar.
    # Copyright (C) ... Foo Company
    # This file is distributed under the same license as the Foobar project.
    # FIRST AUTHOR <EMAIL@ADDRESS>, ....
    #

    The header can also be set from a string. Any known upper-case variables
    will be replaced when the header is retrieved again:

    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   copyright_holder='Foo Company')
    >>> catalog.header_comment = '''\\
    ... # The POT for my really cool PROJECT project.
    ... # Copyright (C) 1990-2003 ORGANIZATION
    ... # This file is distributed under the same license as the PROJECT
    ... # project.
    ... #'''
    >>> print(catalog.header_comment)
    # The POT for my really cool Foobar project.
    # Copyright (C) 1990-2003 Foo Company
    # This file is distributed under the same license as the Foobar
    # project.
    #

    :type: `unicode`
    """)

    def _get_mime_headers(self) -> list[tuple[str, str]]:
        headers: list[tuple[str, str]] = []
        headers.append(("Project-Id-Version", f"{self.project} {self.version}"))
        headers.append(('Report-Msgid-Bugs-To', self.msgid_bugs_address))
        headers.append(('POT-Creation-Date',
                        format_datetime(self.creation_date, 'yyyy-MM-dd HH:mmZ',
                                        locale='en')))
        if isinstance(self.revision_date, (datetime.datetime, datetime.time, int, float)):
            headers.append(('PO-Revision-Date',
                            format_datetime(self.revision_date,
                                            'yyyy-MM-dd HH:mmZ', locale='en')))
        else:
            headers.append(('PO-Revision-Date', self.revision_date))
        headers.append(('Last-Translator', self.last_translator))
        if self.locale_identifier:
            headers.append(('Language', str(self.locale_identifier)))
        if self.locale_identifier and ('LANGUAGE' in self.language_team):
            headers.append(('Language-Team',
                            self.language_team.replace('LANGUAGE',
                                                       str(self.locale_identifier))))
        else:
            headers.append(('Language-Team', self.language_team))
        if self.locale is not None:
            headers.append(('Plural-Forms', self.plural_forms))
        headers.append(('MIME-Version', '1.0'))
        headers.append(("Content-Type", f"text/plain; charset={self.charset}"))
        headers.append(('Content-Transfer-Encoding', '8bit'))
        headers.append(("Generated-By", f"Babel {VERSION}\n"))
        return headers

    def _force_text(self, s: str | bytes, encoding: str = 'utf-8', errors: str = 'strict') -> str:
        if isinstance(s, str):
            return s
        if isinstance(s, bytes):
            return s.decode(encoding, errors)
        return str(s)

    def _set_mime_headers(self, headers: Iterable[tuple[str, str]]) -> None:
        for name, value in headers:
            name = self._force_text(name.lower(), encoding=self.charset)
            value = self._force_text(value, encoding=self.charset)
            if name == 'project-id-version':
                parts = value.split(' ')
                self.project = ' '.join(parts[:-1])
                self.version = parts[-1]
            elif name == 'report-msgid-bugs-to':
                self.msgid_bugs_address = value
            elif name == 'last-translator':
                self.last_translator = value
            elif name == 'language':
                value = value.replace('-', '_')
                self._set_locale(value)
            elif name == 'language-team':
                self.language_team = value
            elif name == 'content-type':
                params = parse_separated_header(value)
                if 'charset' in params:
                    self.charset = params['charset'].lower()
            elif name == 'plural-forms':
                params = parse_separated_header(f" ;{value}")
                self._num_plurals = int(params.get('nplurals', 2))
                self._plural_expr = params.get('plural', '(n != 1)')
            elif name == 'pot-creation-date':
                self.creation_date = _parse_datetime_header(value)
            elif name == 'po-revision-date':
                # Keep the value if it's not the default one
                if 'YEAR' not in value:
                    self.revision_date = _parse_datetime_header(value)

    mime_headers = property(_get_mime_headers, _set_mime_headers, doc="""\
    The MIME headers of the catalog, used for the special ``msgid ""`` entry.

    The behavior of this property changes slightly depending on whether a locale
    is set or not, the latter indicating that the catalog is actually a template
    for actual translations.

    Here's an example of the output for such a catalog template:

    >>> from babel.dates import UTC
    >>> from datetime import datetime
    >>> created = datetime(1990, 4, 1, 15, 30, tzinfo=UTC)
    >>> catalog = Catalog(project='Foobar', version='1.0',
    ...                   creation_date=created)
    >>> for name, value in catalog.mime_headers:
    ...     print('%s: %s' % (name, value))
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE
    Last-Translator: FULL NAME <EMAIL@ADDRESS>
    Language-Team: LANGUAGE <LL@li.org>
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    And here's an example of the output when the locale is set:

    >>> revised = datetime(1990, 8, 3, 12, 0, tzinfo=UTC)
    >>> catalog = Catalog(locale='de_DE', project='Foobar', version='1.0',
    ...                   creation_date=created, revision_date=revised,
    ...                   last_translator='John Doe <jd@example.com>',
    ...                   language_team='de_DE <de@example.com>')
    >>> for name, value in catalog.mime_headers:
    ...     print('%s: %s' % (name, value))
    Project-Id-Version: Foobar 1.0
    Report-Msgid-Bugs-To: EMAIL@ADDRESS
    POT-Creation-Date: 1990-04-01 15:30+0000
    PO-Revision-Date: 1990-08-03 12:00+0000
    Last-Translator: John Doe <jd@example.com>
    Language: de_DE
    Language-Team: de_DE <de@example.com>
    Plural-Forms: nplurals=2; plural=(n != 1);
    MIME-Version: 1.0
    Content-Type: text/plain; charset=utf-8
    Content-Transfer-Encoding: 8bit
    Generated-By: Babel ...

    :type: `list`
    """)

    @property
    def num_plurals(self) -> int:
        """The number of plurals used by the catalog or locale.

        >>> Catalog(locale='en').num_plurals
        2
        >>> Catalog(locale='ga').num_plurals
        5

        :type: `int`"""
        if self._num_plurals is None:
            num = 2
            if self.locale:
                num = get_plural(self.locale)[0]
            self._num_plurals = num
        return self._num_plurals

    @property
    def plural_expr(self) -> str:
        """The plural expression used by the catalog or locale.

        >>> Catalog(locale='en').plural_expr
        '(n != 1)'
        >>> Catalog(locale='ga').plural_expr
        '(n==1 ? 0 : n==2 ? 1 : n>=3 && n<=6 ? 2 : n>=7 && n<=10 ? 3 : 4)'
        >>> Catalog(locale='ding').plural_expr  # unknown locale
        '(n != 1)'

        :type: `str`"""
        if self._plural_expr is None:
            expr = '(n != 1)'
            if self.locale:
                expr = get_plural(self.locale)[1]
            self._plural_expr = expr
        return self._plural_expr

    @property
    def plural_forms(self) -> str:
        """Return the plural forms declaration for the locale.

        >>> Catalog(locale='en').plural_forms
        'nplurals=2; plural=(n != 1);'
        >>> Catalog(locale='pt_BR').plural_forms
        'nplurals=2; plural=(n > 1);'

        :type: `str`"""
        return f"nplurals={self.num_plurals}; plural={self.plural_expr};"

    def __contains__(self, id: _MessageID) -> bool:
        """Return whether the catalog has a message with the specified ID."""
        return self._key_for(id) in self._messages

    def __len__(self) -> int:
        """The number of messages in the catalog.

        This does not include the special ``msgid ""`` entry."""
        return len(self._messages)

    def __iter__(self) -> Iterator[Message]:
        """Iterates through all the entries in the catalog, in the order they
        were added, yielding a `Message` object for every entry.

        :rtype: ``iterator``"""
        buf = []
        for name, value in self.mime_headers:
            buf.append(f"{name}: {value}")
        flags = set()
        if self.fuzzy:
            flags |= {'fuzzy'}
        yield Message('', '\n'.join(buf), flags=flags)
        for key in self._messages:
            yield self._messages[key]

    def __repr__(self) -> str:
        locale = ''
        if self.locale:
            locale = f" {self.locale}"
        return f"<{type(self).__name__} {self.domain!r}{locale}>"

    def __delitem__(self, id: _MessageID) -> None:
        """Delete the message with the specified ID."""
        self.delete(id)

    def __getitem__(self, id: _MessageID) -> Message:
        """Return the message with the specified ID.

        :param id: the message ID
        """
        return self.get(id)

    def __setitem__(self, id: _MessageID, message: Message) -> None:
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo')
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        If a message with that ID is already in the catalog, it is updated
        to include the locations and flags of the new message.

        >>> catalog = Catalog()
        >>> catalog[u'foo'] = Message(u'foo', locations=[('main.py', 1)])
        >>> catalog[u'foo'].locations
        [('main.py', 1)]
        >>> catalog[u'foo'] = Message(u'foo', locations=[('utils.py', 5)])
        >>> catalog[u'foo'].locations
        [('main.py', 1), ('utils.py', 5)]

        :param id: the message ID
        :param message: the `Message` object
        """
        assert isinstance(message, Message), 'expected a Message object'
        key = self._key_for(id, message.context)
        current = self._messages.get(key)
        if current:
            if message.pluralizable and not current.pluralizable:
                # The new message adds pluralization
                current.id = message.id
                current.string = message.string
            current.locations = list(distinct(current.locations +
                                              message.locations))
            current.auto_comments = list(distinct(current.auto_comments +
                                                  message.auto_comments))
            current.user_comments = list(distinct(current.user_comments +
                                                  message.user_comments))
            current.flags |= message.flags
            message = current
        elif id == '':
            # special treatment for the header message
            self.mime_headers = message_from_string(message.string).items()
            self.header_comment = "\n".join([f"# {c}".rstrip() for c in message.user_comments])
            self.fuzzy = message.fuzzy
        else:
            if isinstance(id, (list, tuple)):
                assert isinstance(message.string, (list, tuple)), \
                    f"Expected sequence but got {type(message.string)}"
            self._messages[key] = message

    def add(
        self,
        id: _MessageID,
        string: _MessageID | None = None,
        locations: Iterable[tuple[str, int]] = (),
        flags: Iterable[str] = (),
        auto_comments: Iterable[str] = (),
        user_comments: Iterable[str] = (),
        previous_id: _MessageID = (),
        lineno: int | None = None,
        context: str | None = None,
    ) -> Message:
        """Add or update the message with the specified ID.

        >>> catalog = Catalog()
        >>> catalog.add(u'foo')
        <Message ...>
        >>> catalog[u'foo']
        <Message u'foo' (flags: [])>

        This method simply constructs a `Message` object with the given
        arguments and invokes `__setitem__` with that object.

        :param id: the message ID, or a ``(singular, plural)`` tuple for
                   pluralizable messages
        :param string: the translated message string, or a
                       ``(singular, plural)`` tuple for pluralizable messages
        :param locations: a sequence of ``(filename, lineno)`` tuples
        :param flags: a set or sequence of flags
        :param auto_comments: a sequence of automatic comments
        :param user_comments: a sequence of user comments
        :param previous_id: the previous message ID, or a ``(singular, plural)``
                            tuple for pluralizable messages
        :param lineno: the line number on which the msgid line was found in the
                       PO file, if any
        :param context: the message context
        """
        message = Message(id, string, list(locations), flags, auto_comments,
                          user_comments, previous_id, lineno=lineno,
                          context=context)
        self[id] = message
        return message

    def check(self) -> Iterable[tuple[Message, list[TranslationError]]]:
        """Run various validation checks on the translations in the catalog.

        For every message which fails validation, this method yield a
        ``(message, errors)`` tuple, where ``message`` is the `Message` object
        and ``errors`` is a sequence of `TranslationError` objects.

        :rtype: ``generator`` of ``(message, errors)``
        """
        for message in self._messages.values():
            errors = message.check(catalog=self)
            if errors:
                yield message, errors

    def get(self, id: _MessageID, context: str | None = None) -> Message | None:
        """Return the message with the specified ID and context.

        :param id: the message ID
        :param context: the message context, or ``None`` for no context
        """
        return self._messages.get(self._key_for(id, context))

    def delete(self, id: _MessageID, context: str | None = None) -> None:
        """Delete the message with the specified ID and context.

        :param id: the message ID
        :param context: the message context, or ``None`` for no context
        """
        key = self._key_for(id, context)
        if key in self._messages:
            del self._messages[key]

    def update(
        self,
        template: Catalog,
        no_fuzzy_matching: bool = False,
        update_header_comment: bool = False,
        keep_user_comments: bool = True,
        update_creation_date: bool = True,
    ) -> None:
        """Update the catalog based on the given template catalog.

        >>> from babel.messages import Catalog
        >>> template = Catalog()
        >>> template.add('green', locations=[('main.py', 99)])
        <Message ...>
        >>> template.add('blue', locations=[('main.py', 100)])
        <Message ...>
        >>> template.add(('salad', 'salads'), locations=[('util.py', 42)])
        <Message ...>
        >>> catalog = Catalog(locale='de_DE')
        >>> catalog.add('blue', u'blau', locations=[('main.py', 98)])
        <Message ...>
        >>> catalog.add('head', u'Kopf', locations=[('util.py', 33)])
        <Message ...>
        >>> catalog.add(('salad', 'salads'), (u'Salat', u'Salate'),
        ...             locations=[('util.py', 38)])
        <Message ...>

        >>> catalog.update(template)
        >>> len(catalog)
        3

        >>> msg1 = catalog['green']
        >>> msg1.string
        >>> msg1.locations
        [('main.py', 99)]

        >>> msg2 = catalog['blue']
        >>> msg2.string
        u'blau'
        >>> msg2.locations
        [('main.py', 100)]

        >>> msg3 = catalog['salad']
        >>> msg3.string
        (u'Salat', u'Salate')
        >>> msg3.locations
        [('util.py', 42)]

        Messages that are in the catalog but not in the template are removed
        from the main collection, but can still be accessed via the `obsolete`
        member:

        >>> 'head' in catalog
        False
        >>> list(catalog.obsolete.values())
        [<Message 'head' (flags: [])>]

        :param template: the reference catalog, usually read from a POT file
        :param no_fuzzy_matching: whether to use fuzzy matching of message IDs
        """
        messages = self._messages
        remaining = messages.copy()
        self._messages = OrderedDict()

        # Prepare for fuzzy matching
        fuzzy_candidates = {}
        if not no_fuzzy_matching:
            for msgid in messages:
                if msgid and messages[msgid].string:
                    key = self._key_for(msgid)
                    ctxt = messages[msgid].context
                    fuzzy_candidates[self._to_fuzzy_match_key(key)] = (key, ctxt)
        fuzzy_matches = set()

        def _merge(message: Message, oldkey: tuple[str, str] | str, newkey: tuple[str, str] | str) -> None:
            message = message.clone()
            fuzzy = False
            if oldkey != newkey:
                fuzzy = True
                fuzzy_matches.add(oldkey)
                oldmsg = messages.get(oldkey)
                assert oldmsg is not None
                if isinstance(oldmsg.id, str):
                    message.previous_id = [oldmsg.id]
                else:
                    message.previous_id = list(oldmsg.id)
            else:
                oldmsg = remaining.pop(oldkey, None)
                assert oldmsg is not None
            message.string = oldmsg.string

            if keep_user_comments:
                message.user_comments = list(distinct(oldmsg.user_comments))

            if isinstance(message.id, (list, tuple)):
                if not isinstance(message.string, (list, tuple)):
                    fuzzy = True
                    message.string = tuple(
                        [message.string] + ([''] * (len(message.id) - 1)),
                    )
                elif len(message.string) != self.num_plurals:
                    fuzzy = True
                    message.string = tuple(message.string[:len(oldmsg.string)])
            elif isinstance(message.string, (list, tuple)):
                fuzzy = True
                message.string = message.string[0]
            message.flags |= oldmsg.flags
            if fuzzy:
                message.flags |= {'fuzzy'}
            self[message.id] = message

        for message in template:
            if message.id:
                key = self._key_for(message.id, message.context)
                if key in messages:
                    _merge(message, key, key)
                else:
                    if not no_fuzzy_matching:
                        # do some fuzzy matching with difflib
                        matches = get_close_matches(
                            self._to_fuzzy_match_key(key),
                            fuzzy_candidates.keys(),
                            1,
                        )
                        if matches:
                            modified_key = matches[0]
                            newkey, newctxt = fuzzy_candidates[modified_key]
                            if newctxt is not None:
                                newkey = newkey, newctxt
                            _merge(message, newkey, key)
                            continue

                    self[message.id] = message

        for msgid in remaining:
            if no_fuzzy_matching or msgid not in fuzzy_matches:
                self.obsolete[msgid] = remaining[msgid]

        if update_header_comment:
            # Allow the updated catalog's header to be rewritten based on the
            # template's header
            self.header_comment = template.header_comment

        # Make updated catalog's POT-Creation-Date equal to the template
        # used to update the catalog
        if update_creation_date:
            self.creation_date = template.creation_date

    def _to_fuzzy_match_key(self, key: tuple[str, str] | str) -> str:
        """Converts a message key to a string suitable for fuzzy matching."""
        if isinstance(key, tuple):
            matchkey = key[0]  # just the msgid, no context
        else:
            matchkey = key
        return matchkey.lower().strip()

    def _key_for(self, id: _MessageID, context: str | None = None) -> tuple[str, str] | str:
        """The key for a message is just the singular ID even for pluralizable
        messages, but is a ``(msgid, msgctxt)`` tuple for context-specific
        messages.
        """
        key = id
        if isinstance(key, (list, tuple)):
            key = id[0]
        if context is not None:
            key = (key, context)
        return key

    def is_identical(self, other: Catalog) -> bool:
        """Checks if catalogs are identical, taking into account messages and
        headers.
        """
        assert isinstance(other, Catalog)
        for key in self._messages.keys() | other._messages.keys():
            message_1 = self.get(key)
            message_2 = other.get(key)
            if (
                message_1 is None
                or message_2 is None
                or not message_1.is_identical(message_2)
            ):
                return False
        return dict(self.mime_headers) == dict(other.mime_headers)
