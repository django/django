"""Builder superclass for all builders."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from os import path
from typing import TYPE_CHECKING, Callable, NamedTuple

import babel.dates
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po

from sphinx.errors import SphinxError
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.osutil import SEP, canon_path, relpath

if TYPE_CHECKING:
    from collections.abc import Generator

    from sphinx.environment import BuildEnvironment


logger = logging.getLogger(__name__)


class LocaleFileInfoBase(NamedTuple):
    base_dir: str
    domain: str
    charset: str


class CatalogInfo(LocaleFileInfoBase):

    @property
    def po_file(self) -> str:
        return self.domain + '.po'

    @property
    def mo_file(self) -> str:
        return self.domain + '.mo'

    @property
    def po_path(self) -> str:
        return path.join(self.base_dir, self.po_file)

    @property
    def mo_path(self) -> str:
        return path.join(self.base_dir, self.mo_file)

    def is_outdated(self) -> bool:
        return (
            not path.exists(self.mo_path) or
            path.getmtime(self.mo_path) < path.getmtime(self.po_path))

    def write_mo(self, locale: str, use_fuzzy: bool = False) -> None:
        with open(self.po_path, encoding=self.charset) as file_po:
            try:
                po = read_po(file_po, locale)
            except Exception as exc:
                logger.warning(__('reading error: %s, %s'), self.po_path, exc)
                return

        with open(self.mo_path, 'wb') as file_mo:
            try:
                write_mo(file_mo, po, use_fuzzy)
            except Exception as exc:
                logger.warning(__('writing error: %s, %s'), self.mo_path, exc)


class CatalogRepository:
    """A repository for message catalogs."""

    def __init__(self, basedir: str | os.PathLike[str], locale_dirs: list[str],
                 language: str, encoding: str) -> None:
        self.basedir = basedir
        self._locale_dirs = locale_dirs
        self.language = language
        self.encoding = encoding

    @property
    def locale_dirs(self) -> Generator[str, None, None]:
        if not self.language:
            return

        for locale_dir in self._locale_dirs:
            locale_dir = path.join(self.basedir, locale_dir)
            locale_path = path.join(locale_dir, self.language, 'LC_MESSAGES')
            if path.exists(locale_path):
                yield locale_dir
            else:
                logger.verbose(__('locale_dir %s does not exist'), locale_path)

    @property
    def pofiles(self) -> Generator[tuple[str, str], None, None]:
        for locale_dir in self.locale_dirs:
            basedir = path.join(locale_dir, self.language, 'LC_MESSAGES')
            for root, dirnames, filenames in os.walk(basedir):
                # skip dot-directories
                for dirname in dirnames:
                    if dirname.startswith('.'):
                        dirnames.remove(dirname)

                for filename in filenames:
                    if filename.endswith('.po'):
                        fullpath = path.join(root, filename)
                        yield basedir, relpath(fullpath, basedir)

    @property
    def catalogs(self) -> Generator[CatalogInfo, None, None]:
        for basedir, filename in self.pofiles:
            domain = canon_path(path.splitext(filename)[0])
            yield CatalogInfo(basedir, domain, self.encoding)


def docname_to_domain(docname: str, compaction: bool | str) -> str:
    """Convert docname to domain for catalogs."""
    if isinstance(compaction, str):
        return compaction
    if compaction:
        return docname.split(SEP, 1)[0]
    else:
        return docname


# date_format mappings: ustrftime() to babel.dates.format_datetime()
date_format_mappings = {
    '%a':  'EEE',     # Weekday as locale’s abbreviated name.
    '%A':  'EEEE',    # Weekday as locale’s full name.
    '%b':  'MMM',     # Month as locale’s abbreviated name.
    '%B':  'MMMM',    # Month as locale’s full name.
    '%c':  'medium',  # Locale’s appropriate date and time representation.
    '%-d': 'd',       # Day of the month as a decimal number.
    '%d':  'dd',      # Day of the month as a zero-padded decimal number.
    '%-H': 'H',       # Hour (24-hour clock) as a decimal number [0,23].
    '%H':  'HH',      # Hour (24-hour clock) as a zero-padded decimal number [00,23].
    '%-I': 'h',       # Hour (12-hour clock) as a decimal number [1,12].
    '%I':  'hh',      # Hour (12-hour clock) as a zero-padded decimal number [01,12].
    '%-j': 'D',       # Day of the year as a decimal number.
    '%j':  'DDD',     # Day of the year as a zero-padded decimal number.
    '%-m': 'M',       # Month as a decimal number.
    '%m':  'MM',      # Month as a zero-padded decimal number.
    '%-M': 'm',       # Minute as a decimal number [0,59].
    '%M':  'mm',      # Minute as a zero-padded decimal number [00,59].
    '%p':  'a',       # Locale’s equivalent of either AM or PM.
    '%-S': 's',       # Second as a decimal number.
    '%S':  'ss',      # Second as a zero-padded decimal number.
    '%U':  'WW',      # Week number of the year (Sunday as the first day of the week)
                      # as a zero padded decimal number. All days in a new year preceding
                      # the first Sunday are considered to be in week 0.
    '%w':  'e',       # Weekday as a decimal number, where 0 is Sunday and 6 is Saturday.
    '%-W': 'W',       # Week number of the year (Monday as the first day of the week)
                      # as a decimal number. All days in a new year preceding the first
                      # Monday are considered to be in week 0.
    '%W':  'WW',      # Week number of the year (Monday as the first day of the week)
                      # as a zero-padded decimal number.
    '%x':  'medium',  # Locale’s appropriate date representation.
    '%X':  'medium',  # Locale’s appropriate time representation.
    '%y':  'YY',      # Year without century as a zero-padded decimal number.
    '%Y':  'yyyy',    # Year with century as a decimal number.
    '%Z':  'zzz',     # Time zone name (no characters if no time zone exists).
    '%z':  'ZZZ',     # UTC offset in the form ±HHMM[SS[.ffffff]]
                      # (empty string if the object is naive).
    '%%':  '%',
}

date_format_re = re.compile('(%s)' % '|'.join(date_format_mappings))


def babel_format_date(date: datetime, format: str, locale: str,
                      formatter: Callable = babel.dates.format_date) -> str:
    # Check if we have the tzinfo attribute. If not we cannot do any time
    # related formats.
    if not hasattr(date, 'tzinfo'):
        formatter = babel.dates.format_date

    try:
        return formatter(date, format, locale=locale)
    except (ValueError, babel.core.UnknownLocaleError):
        # fallback to English
        return formatter(date, format, locale='en')
    except AttributeError:
        logger.warning(__('Invalid date format. Quote the string by single quote '
                          'if you want to output it directly: %s'), format)
        return format


def format_date(
    format: str, *, date: datetime | None = None, language: str,
) -> str:
    if date is None:
        # If time is not specified, try to use $SOURCE_DATE_EPOCH variable
        # See https://wiki.debian.org/ReproducibleBuilds/TimestampsProposal
        source_date_epoch = os.getenv('SOURCE_DATE_EPOCH')
        if source_date_epoch is not None:
            date = datetime.fromtimestamp(float(source_date_epoch), tz=timezone.utc)
        else:
            date = datetime.now(tz=timezone.utc).astimezone()

    result = []
    tokens = date_format_re.split(format)
    for token in tokens:
        if token in date_format_mappings:
            babel_format = date_format_mappings.get(token, '')

            # Check if we have to use a different babel formatter then
            # format_datetime, because we only want to format a date
            # or a time.
            if token == '%x':
                function = babel.dates.format_date
            elif token == '%X':
                function = babel.dates.format_time
            else:
                function = babel.dates.format_datetime

            result.append(babel_format_date(date, babel_format, locale=language,
                                            formatter=function))
        else:
            result.append(token)

    return "".join(result)


def get_image_filename_for_language(
    filename: str | os.PathLike[str],
    env: BuildEnvironment,
) -> str:
    root, ext = path.splitext(filename)
    dirname = path.dirname(root)
    docpath = path.dirname(env.docname)
    try:
        return env.config.figure_language_filename.format(
            root=root,
            ext=ext,
            path=dirname and dirname + SEP,
            basename=path.basename(root),
            docpath=docpath and docpath + SEP,
            language=env.config.language,
        )
    except KeyError as exc:
        msg = f'Invalid figure_language_filename: {exc!r}'
        raise SphinxError(msg) from exc


def search_image_for_language(filename: str, env: BuildEnvironment) -> str:
    translated = get_image_filename_for_language(filename, env)
    _, abspath = env.relfn2path(translated)
    if path.exists(abspath):
        return translated
    else:
        return filename
