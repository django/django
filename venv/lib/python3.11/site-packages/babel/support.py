"""
    babel.support
    ~~~~~~~~~~~~~

    Several classes and functions that help with integrating and using Babel
    in applications.

    .. note: the code in this module is not used by Babel itself

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import annotations

import decimal
import gettext
import locale
import os
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Callable, Iterable

from babel.core import Locale
from babel.dates import format_date, format_datetime, format_time, format_timedelta
from babel.numbers import (
    format_compact_currency,
    format_compact_decimal,
    format_currency,
    format_decimal,
    format_percent,
    format_scientific,
)

if TYPE_CHECKING:
    from typing_extensions import Literal

    from babel.dates import _PredefinedTimeFormat


class Format:
    """Wrapper class providing the various date and number formatting functions
    bound to a specific locale and time-zone.

    >>> from babel.util import UTC
    >>> from datetime import date
    >>> fmt = Format('en_US', UTC)
    >>> fmt.date(date(2007, 4, 1))
    u'Apr 1, 2007'
    >>> fmt.decimal(1.2345)
    u'1.234'
    """

    def __init__(
        self,
        locale: Locale | str,
        tzinfo: datetime.tzinfo | None = None,
        *,
        numbering_system: Literal["default"] | str = "latn",
    ) -> None:
        """Initialize the formatter.

        :param locale: the locale identifier or `Locale` instance
        :param tzinfo: the time-zone info (a `tzinfo` instance or `None`)
        :param numbering_system: The numbering system used for formatting number symbols. Defaults to "latn".
                                 The special value "default" will use the default numbering system of the locale.
        """
        self.locale = Locale.parse(locale)
        self.tzinfo = tzinfo
        self.numbering_system = numbering_system

    def date(
        self,
        date: datetime.date | None = None,
        format: _PredefinedTimeFormat | str = 'medium',
    ) -> str:
        """Return a date formatted according to the given pattern.

        >>> from datetime import date
        >>> fmt = Format('en_US')
        >>> fmt.date(date(2007, 4, 1))
        u'Apr 1, 2007'
        """
        return format_date(date, format, locale=self.locale)

    def datetime(
        self,
        datetime: datetime.date | None = None,
        format: _PredefinedTimeFormat | str = 'medium',
    ) -> str:
        """Return a date and time formatted according to the given pattern.

        >>> from datetime import datetime
        >>> from babel.dates import get_timezone
        >>> fmt = Format('en_US', tzinfo=get_timezone('US/Eastern'))
        >>> fmt.datetime(datetime(2007, 4, 1, 15, 30))
        u'Apr 1, 2007, 11:30:00\u202fAM'
        """
        return format_datetime(datetime, format, tzinfo=self.tzinfo, locale=self.locale)

    def time(
        self,
        time: datetime.time | datetime.datetime | None = None,
        format: _PredefinedTimeFormat | str = 'medium',
    ) -> str:
        """Return a time formatted according to the given pattern.

        >>> from datetime import datetime
        >>> from babel.dates import get_timezone
        >>> fmt = Format('en_US', tzinfo=get_timezone('US/Eastern'))
        >>> fmt.time(datetime(2007, 4, 1, 15, 30))
        u'11:30:00\u202fAM'
        """
        return format_time(time, format, tzinfo=self.tzinfo, locale=self.locale)

    def timedelta(
        self,
        delta: datetime.timedelta | int,
        granularity: Literal["year", "month", "week", "day", "hour", "minute", "second"] = "second",
        threshold: float = 0.85,
        format: Literal["narrow", "short", "medium", "long"] = "long",
        add_direction: bool = False,
    ) -> str:
        """Return a time delta according to the rules of the given locale.

        >>> from datetime import timedelta
        >>> fmt = Format('en_US')
        >>> fmt.timedelta(timedelta(weeks=11))
        u'3 months'
        """
        return format_timedelta(delta, granularity=granularity,
                                threshold=threshold,
                                format=format, add_direction=add_direction,
                                locale=self.locale)

    def number(self, number: float | decimal.Decimal | str) -> str:
        """Return an integer number formatted for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.number(1099)
        u'1,099'
        """
        return format_decimal(number, locale=self.locale, numbering_system=self.numbering_system)

    def decimal(self, number: float | decimal.Decimal | str, format: str | None = None) -> str:
        """Return a decimal number formatted for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.decimal(1.2345)
        u'1.234'
        """
        return format_decimal(number, format, locale=self.locale, numbering_system=self.numbering_system)

    def compact_decimal(
        self,
        number: float | decimal.Decimal | str,
        format_type: Literal['short', 'long'] = 'short',
        fraction_digits: int = 0,
    ) -> str:
        """Return a number formatted in compact form for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.compact_decimal(123456789)
        u'123M'
        >>> fmt.compact_decimal(1234567, format_type='long', fraction_digits=2)
        '1.23 million'
        """
        return format_compact_decimal(
            number,
            format_type=format_type,
            fraction_digits=fraction_digits,
            locale=self.locale,
            numbering_system=self.numbering_system,
        )

    def currency(self, number: float | decimal.Decimal | str, currency: str) -> str:
        """Return a number in the given currency formatted for the locale.
        """
        return format_currency(number, currency, locale=self.locale, numbering_system=self.numbering_system)

    def compact_currency(
        self,
        number: float | decimal.Decimal | str,
        currency: str,
        format_type: Literal['short'] = 'short',
        fraction_digits: int = 0,
    ) -> str:
        """Return a number in the given currency formatted for the locale
        using the compact number format.

        >>> Format('en_US').compact_currency(1234567, "USD", format_type='short', fraction_digits=2)
        '$1.23M'
        """
        return format_compact_currency(number, currency, format_type=format_type, fraction_digits=fraction_digits,
                                       locale=self.locale, numbering_system=self.numbering_system)

    def percent(self, number: float | decimal.Decimal | str, format: str | None = None) -> str:
        """Return a number formatted as percentage for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.percent(0.34)
        u'34%'
        """
        return format_percent(number, format, locale=self.locale, numbering_system=self.numbering_system)

    def scientific(self, number: float | decimal.Decimal | str) -> str:
        """Return a number formatted using scientific notation for the locale.
        """
        return format_scientific(number, locale=self.locale, numbering_system=self.numbering_system)


class LazyProxy:
    """Class for proxy objects that delegate to a specified function to evaluate
    the actual object.

    >>> def greeting(name='world'):
    ...     return 'Hello, %s!' % name
    >>> lazy_greeting = LazyProxy(greeting, name='Joe')
    >>> print(lazy_greeting)
    Hello, Joe!
    >>> u'  ' + lazy_greeting
    u'  Hello, Joe!'
    >>> u'(%s)' % lazy_greeting
    u'(Hello, Joe!)'

    This can be used, for example, to implement lazy translation functions that
    delay the actual translation until the string is actually used. The
    rationale for such behavior is that the locale of the user may not always
    be available. In web applications, you only know the locale when processing
    a request.

    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting:

    >>> greetings = [
    ...     LazyProxy(greeting, 'world'),
    ...     LazyProxy(greeting, 'Joe'),
    ...     LazyProxy(greeting, 'universe'),
    ... ]
    >>> greetings.sort()
    >>> for greeting in greetings:
    ...     print(greeting)
    Hello, Joe!
    Hello, universe!
    Hello, world!
    """
    __slots__ = ['_func', '_args', '_kwargs', '_value', '_is_cache_enabled', '_attribute_error']

    if TYPE_CHECKING:
        _func: Callable[..., Any]
        _args: tuple[Any, ...]
        _kwargs: dict[str, Any]
        _is_cache_enabled: bool
        _value: Any
        _attribute_error: AttributeError | None

    def __init__(self, func: Callable[..., Any], *args: Any, enable_cache: bool = True, **kwargs: Any) -> None:
        # Avoid triggering our own __setattr__ implementation
        object.__setattr__(self, '_func', func)
        object.__setattr__(self, '_args', args)
        object.__setattr__(self, '_kwargs', kwargs)
        object.__setattr__(self, '_is_cache_enabled', enable_cache)
        object.__setattr__(self, '_value', None)
        object.__setattr__(self, '_attribute_error', None)

    @property
    def value(self) -> Any:
        if self._value is None:
            try:
                value = self._func(*self._args, **self._kwargs)
            except AttributeError as error:
                object.__setattr__(self, '_attribute_error', error)
                raise

            if not self._is_cache_enabled:
                return value
            object.__setattr__(self, '_value', value)
        return self._value

    def __contains__(self, key: object) -> bool:
        return key in self.value

    def __bool__(self) -> bool:
        return bool(self.value)

    def __dir__(self) -> list[str]:
        return dir(self.value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self.value)

    def __len__(self) -> int:
        return len(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __add__(self, other: object) -> Any:
        return self.value + other

    def __radd__(self, other: object) -> Any:
        return other + self.value

    def __mod__(self, other: object) -> Any:
        return self.value % other

    def __rmod__(self, other: object) -> Any:
        return other % self.value

    def __mul__(self, other: object) -> Any:
        return self.value * other

    def __rmul__(self, other: object) -> Any:
        return other * self.value

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.value(*args, **kwargs)

    def __lt__(self, other: object) -> bool:
        return self.value < other

    def __le__(self, other: object) -> bool:
        return self.value <= other

    def __eq__(self, other: object) -> bool:
        return self.value == other

    def __ne__(self, other: object) -> bool:
        return self.value != other

    def __gt__(self, other: object) -> bool:
        return self.value > other

    def __ge__(self, other: object) -> bool:
        return self.value >= other

    def __delattr__(self, name: str) -> None:
        delattr(self.value, name)

    def __getattr__(self, name: str) -> Any:
        if self._attribute_error is not None:
            raise self._attribute_error
        return getattr(self.value, name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self.value, name, value)

    def __delitem__(self, key: Any) -> None:
        del self.value[key]

    def __getitem__(self, key: Any) -> Any:
        return self.value[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self.value[key] = value

    def __copy__(self) -> LazyProxy:
        return LazyProxy(
            self._func,
            enable_cache=self._is_cache_enabled,
            *self._args,  # noqa: B026
            **self._kwargs,
        )

    def __deepcopy__(self, memo: Any) -> LazyProxy:
        from copy import deepcopy
        return LazyProxy(
            deepcopy(self._func, memo),
            enable_cache=deepcopy(self._is_cache_enabled, memo),
            *deepcopy(self._args, memo),  # noqa: B026
            **deepcopy(self._kwargs, memo),
        )


class NullTranslations(gettext.NullTranslations):

    if TYPE_CHECKING:
        _info: dict[str, str]
        _fallback: NullTranslations | None

    DEFAULT_DOMAIN = None

    def __init__(self, fp: gettext._TranslationsReader | None = None) -> None:
        """Initialize a simple translations class which is not backed by a
        real catalog. Behaves similar to gettext.NullTranslations but also
        offers Babel's on *gettext methods (e.g. 'dgettext()').

        :param fp: a file-like object (ignored in this class)
        """
        # These attributes are set by gettext.NullTranslations when a catalog
        # is parsed (fp != None). Ensure that they are always present because
        # some *gettext methods (including '.gettext()') rely on the attributes.
        self._catalog: dict[tuple[str, Any] | str, str] = {}
        self.plural: Callable[[float | decimal.Decimal], int] = lambda n: int(n != 1)
        super().__init__(fp=fp)
        self.files = list(filter(None, [getattr(fp, 'name', None)]))
        self.domain = self.DEFAULT_DOMAIN
        self._domains: dict[str, NullTranslations] = {}

    def dgettext(self, domain: str, message: str) -> str:
        """Like ``gettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).gettext(message)

    def ldgettext(self, domain: str, message: str) -> str:
        """Like ``lgettext()``, but look the message up in the specified
        domain.
        """
        import warnings
        warnings.warn(
            'ldgettext() is deprecated, use dgettext() instead',
            DeprecationWarning,
            stacklevel=2,
        )
        return self._domains.get(domain, self).lgettext(message)

    def udgettext(self, domain: str, message: str) -> str:
        """Like ``ugettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ugettext(message)
    # backward compatibility with 0.9
    dugettext = udgettext

    def dngettext(self, domain: str, singular: str, plural: str, num: int) -> str:
        """Like ``ngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ngettext(singular, plural, num)

    def ldngettext(self, domain: str, singular: str, plural: str, num: int) -> str:
        """Like ``lngettext()``, but look the message up in the specified
        domain.
        """
        import warnings
        warnings.warn(
            'ldngettext() is deprecated, use dngettext() instead',
            DeprecationWarning,
            stacklevel=2,
        )
        return self._domains.get(domain, self).lngettext(singular, plural, num)

    def udngettext(self, domain: str, singular: str, plural: str, num: int) -> str:
        """Like ``ungettext()`` but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ungettext(singular, plural, num)
    # backward compatibility with 0.9
    dungettext = udngettext

    # Most of the downwards code, until it gets included in stdlib, from:
    #    https://bugs.python.org/file10036/gettext-pgettext.patch
    #
    # The encoding of a msgctxt and a msgid in a .mo file is
    # msgctxt + "\x04" + msgid (gettext version >= 0.15)
    CONTEXT_ENCODING = '%s\x04%s'

    def pgettext(self, context: str, message: str) -> str | object:
        """Look up the `context` and `message` id in the catalog and return the
        corresponding message string, as an 8-bit string encoded with the
        catalog's charset encoding, if known.  If there is no entry in the
        catalog for the `message` id and `context` , and a fallback has been
        set, the look up is forwarded to the fallback's ``pgettext()``
        method. Otherwise, the `message` id is returned.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, message)
        missing = object()
        tmsg = self._catalog.get(ctxt_msg_id, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.pgettext(context, message)
            return message
        return tmsg

    def lpgettext(self, context: str, message: str) -> str | bytes | object:
        """Equivalent to ``pgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        import warnings
        warnings.warn(
            'lpgettext() is deprecated, use pgettext() instead',
            DeprecationWarning,
            stacklevel=2,
        )
        tmsg = self.pgettext(context, message)
        encoding = getattr(self, "_output_charset", None) or locale.getpreferredencoding()
        return tmsg.encode(encoding) if isinstance(tmsg, str) else tmsg

    def npgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        """Do a plural-forms lookup of a message id.  `singular` is used as the
        message id for purposes of lookup in the catalog, while `num` is used to
        determine which plural form to use.  The returned message string is an
        8-bit string encoded with the catalog's charset encoding, if known.

        If the message id for `context` is not found in the catalog, and a
        fallback is specified, the request is forwarded to the fallback's
        ``npgettext()`` method.  Otherwise, when ``num`` is 1 ``singular`` is
        returned, and ``plural`` is returned in all other cases.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_msg_id, self.plural(num))]
            return tmsg
        except KeyError:
            if self._fallback:
                return self._fallback.npgettext(context, singular, plural, num)
            if num == 1:
                return singular
            else:
                return plural

    def lnpgettext(self, context: str, singular: str, plural: str, num: int) -> str | bytes:
        """Equivalent to ``npgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        import warnings
        warnings.warn(
            'lnpgettext() is deprecated, use npgettext() instead',
            DeprecationWarning,
            stacklevel=2,
        )
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_msg_id, self.plural(num))]
            encoding = getattr(self, "_output_charset", None) or locale.getpreferredencoding()
            return tmsg.encode(encoding)
        except KeyError:
            if self._fallback:
                return self._fallback.lnpgettext(context, singular, plural, num)
            if num == 1:
                return singular
            else:
                return plural

    def upgettext(self, context: str, message: str) -> str:
        """Look up the `context` and `message` id in the catalog and return the
        corresponding message string, as a Unicode string.  If there is no entry
        in the catalog for the `message` id and `context`, and a fallback has
        been set, the look up is forwarded to the fallback's ``upgettext()``
        method.  Otherwise, the `message` id is returned.
        """
        ctxt_message_id = self.CONTEXT_ENCODING % (context, message)
        missing = object()
        tmsg = self._catalog.get(ctxt_message_id, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.upgettext(context, message)
            return str(message)
        assert isinstance(tmsg, str)
        return tmsg

    def unpgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        """Do a plural-forms lookup of a message id.  `singular` is used as the
        message id for purposes of lookup in the catalog, while `num` is used to
        determine which plural form to use.  The returned message string is a
        Unicode string.

        If the message id for `context` is not found in the catalog, and a
        fallback is specified, the request is forwarded to the fallback's
        ``unpgettext()`` method.  Otherwise, when `num` is 1 `singular` is
        returned, and `plural` is returned in all other cases.
        """
        ctxt_message_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_message_id, self.plural(num))]
        except KeyError:
            if self._fallback:
                return self._fallback.unpgettext(context, singular, plural, num)
            tmsg = str(singular) if num == 1 else str(plural)
        return tmsg

    def dpgettext(self, domain: str, context: str, message: str) -> str | object:
        """Like `pgettext()`, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).pgettext(context, message)

    def udpgettext(self, domain: str, context: str, message: str) -> str:
        """Like `upgettext()`, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).upgettext(context, message)
    # backward compatibility with 0.9
    dupgettext = udpgettext

    def ldpgettext(self, domain: str, context: str, message: str) -> str | bytes | object:
        """Equivalent to ``dpgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        return self._domains.get(domain, self).lpgettext(context, message)

    def dnpgettext(self, domain: str, context: str, singular: str, plural: str, num: int) -> str:
        """Like ``npgettext``, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).npgettext(context, singular,
                                                         plural, num)

    def udnpgettext(self, domain: str, context: str, singular: str, plural: str, num: int) -> str:
        """Like ``unpgettext``, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).unpgettext(context, singular,
                                                          plural, num)
    # backward compatibility with 0.9
    dunpgettext = udnpgettext

    def ldnpgettext(self, domain: str, context: str, singular: str, plural: str, num: int) -> str | bytes:
        """Equivalent to ``dnpgettext()``, but the translation is returned in
        the preferred system encoding, if no other encoding was explicitly set
        with ``bind_textdomain_codeset()``.
        """
        return self._domains.get(domain, self).lnpgettext(context, singular,
                                                          plural, num)

    ugettext = gettext.NullTranslations.gettext
    ungettext = gettext.NullTranslations.ngettext


class Translations(NullTranslations, gettext.GNUTranslations):
    """An extended translation catalog class."""

    DEFAULT_DOMAIN = 'messages'

    def __init__(self, fp: gettext._TranslationsReader | None = None, domain: str | None = None):
        """Initialize the translations catalog.

        :param fp: the file-like object the translation should be read from
        :param domain: the message domain (default: 'messages')
        """
        super().__init__(fp=fp)
        self.domain = domain or self.DEFAULT_DOMAIN

    ugettext = gettext.GNUTranslations.gettext
    ungettext = gettext.GNUTranslations.ngettext

    @classmethod
    def load(
        cls,
        dirname: str | os.PathLike[str] | None = None,
        locales: Iterable[str | Locale] | str | Locale | None = None,
        domain: str | None = None,
    ) -> NullTranslations:
        """Load translations from the given directory.

        :param dirname: the directory containing the ``MO`` files
        :param locales: the list of locales in order of preference (items in
                        this list can be either `Locale` objects or locale
                        strings)
        :param domain: the message domain (default: 'messages')
        """
        if not domain:
            domain = cls.DEFAULT_DOMAIN
        filename = gettext.find(domain, dirname, _locales_to_names(locales))
        if not filename:
            return NullTranslations()
        with open(filename, 'rb') as fp:
            return cls(fp=fp, domain=domain)

    def __repr__(self) -> str:
        version = self._info.get('project-id-version')
        return f'<{type(self).__name__}: "{version}">'

    def add(self, translations: Translations, merge: bool = True):
        """Add the given translations to the catalog.

        If the domain of the translations is different than that of the
        current catalog, they are added as a catalog that is only accessible
        by the various ``d*gettext`` functions.

        :param translations: the `Translations` instance with the messages to
                             add
        :param merge: whether translations for message domains that have
                      already been added should be merged with the existing
                      translations
        """
        domain = getattr(translations, 'domain', self.DEFAULT_DOMAIN)
        if merge and domain == self.domain:
            return self.merge(translations)

        existing = self._domains.get(domain)
        if merge and isinstance(existing, Translations):
            existing.merge(translations)
        else:
            translations.add_fallback(self)
            self._domains[domain] = translations

        return self

    def merge(self, translations: Translations):
        """Merge the given translations into the catalog.

        Message translations in the specified catalog override any messages
        with the same identifier in the existing catalog.

        :param translations: the `Translations` instance with the messages to
                             merge
        """
        if isinstance(translations, gettext.GNUTranslations):
            self._catalog.update(translations._catalog)
            if isinstance(translations, Translations):
                self.files.extend(translations.files)

        return self


def _locales_to_names(
    locales: Iterable[str | Locale] | str | Locale | None,
) -> list[str] | None:
    """Normalize a `locales` argument to a list of locale names.

    :param locales: the list of locales in order of preference (items in
                    this list can be either `Locale` objects or locale
                    strings)
    """
    if locales is None:
        return None
    if isinstance(locales, Locale):
        return [str(locales)]
    if isinstance(locales, str):
        return [locales]
    return [str(locale) for locale in locales]
