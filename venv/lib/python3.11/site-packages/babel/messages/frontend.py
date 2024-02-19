"""
    babel.messages.frontend
    ~~~~~~~~~~~~~~~~~~~~~~~

    Frontends for the message extraction functionality.

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import annotations

import datetime
import fnmatch
import logging
import optparse
import os
import re
import shutil
import sys
import tempfile
from collections import OrderedDict
from configparser import RawConfigParser
from io import StringIO
from typing import Iterable

from babel import Locale, localedata
from babel import __version__ as VERSION
from babel.core import UnknownLocaleError
from babel.messages.catalog import DEFAULT_HEADER, Catalog
from babel.messages.extract import (
    DEFAULT_KEYWORDS,
    DEFAULT_MAPPING,
    check_and_call_extract_file,
    extract_from_dir,
)
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po
from babel.util import LOCALTZ

log = logging.getLogger('babel')


class BaseError(Exception):
    pass


class OptionError(BaseError):
    pass


class SetupError(BaseError):
    pass


def listify_value(arg, split=None):
    """
    Make a list out of an argument.

    Values from `distutils` argument parsing are always single strings;
    values from `optparse` parsing may be lists of strings that may need
    to be further split.

    No matter the input, this function returns a flat list of whitespace-trimmed
    strings, with `None` values filtered out.

    >>> listify_value("foo bar")
    ['foo', 'bar']
    >>> listify_value(["foo bar"])
    ['foo', 'bar']
    >>> listify_value([["foo"], "bar"])
    ['foo', 'bar']
    >>> listify_value([["foo"], ["bar", None, "foo"]])
    ['foo', 'bar', 'foo']
    >>> listify_value("foo, bar, quux", ",")
    ['foo', 'bar', 'quux']

    :param arg: A string or a list of strings
    :param split: The argument to pass to `str.split()`.
    :return:
    """
    out = []

    if not isinstance(arg, (list, tuple)):
        arg = [arg]

    for val in arg:
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            out.extend(listify_value(val, split=split))
            continue
        out.extend(s.strip() for s in str(val).split(split))
    assert all(isinstance(val, str) for val in out)
    return out


class CommandMixin:
    # This class is a small shim between Distutils commands and
    # optparse option parsing in the frontend command line.

    #: Option name to be input as `args` on the script command line.
    as_args = None

    #: Options which allow multiple values.
    #: This is used by the `optparse` transmogrification code.
    multiple_value_options = ()

    #: Options which are booleans.
    #: This is used by the `optparse` transmogrification code.
    # (This is actually used by distutils code too, but is never
    # declared in the base class.)
    boolean_options = ()

    #: Option aliases, to retain standalone command compatibility.
    #: Distutils does not support option aliases, but optparse does.
    #: This maps the distutils argument name to an iterable of aliases
    #: that are usable with optparse.
    option_aliases = {}

    #: Choices for options that needed to be restricted to specific
    #: list of choices.
    option_choices = {}

    #: Log object. To allow replacement in the script command line runner.
    log = log

    def __init__(self, dist=None):
        # A less strict version of distutils' `__init__`.
        self.distribution = dist
        self.initialize_options()
        self._dry_run = None
        self.verbose = False
        self.force = None
        self.help = 0
        self.finalized = 0

    def initialize_options(self):
        pass

    def ensure_finalized(self):
        if not self.finalized:
            self.finalize_options()
        self.finalized = 1

    def finalize_options(self):
        raise RuntimeError(
            f"abstract method -- subclass {self.__class__} must override",
        )


class CompileCatalog(CommandMixin):
    description = 'compile message catalogs to binary MO files'
    user_options = [
        ('domain=', 'D',
         "domains of PO files (space separated list, default 'messages')"),
        ('directory=', 'd',
         'path to base directory containing the catalogs'),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.mo')"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('use-fuzzy', 'f',
         'also include fuzzy translations'),
        ('statistics', None,
         'print statistics about translations'),
    ]
    boolean_options = ['use-fuzzy', 'statistics']

    def initialize_options(self):
        self.domain = 'messages'
        self.directory = None
        self.input_file = None
        self.output_file = None
        self.locale = None
        self.use_fuzzy = False
        self.statistics = False

    def finalize_options(self):
        self.domain = listify_value(self.domain)
        if not self.input_file and not self.directory:
            raise OptionError('you must specify either the input file or the base directory')
        if not self.output_file and not self.directory:
            raise OptionError('you must specify either the output file or the base directory')

    def run(self):
        n_errors = 0
        for domain in self.domain:
            for errors in self._run_domain(domain).values():
                n_errors += len(errors)
        if n_errors:
            self.log.error('%d errors encountered.', n_errors)
        return (1 if n_errors else 0)

    def _run_domain(self, domain):
        po_files = []
        mo_files = []

        if not self.input_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.directory, self.locale,
                                              'LC_MESSAGES',
                                              f"{domain}.po")))
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             f"{domain}.mo"))
            else:
                for locale in os.listdir(self.directory):
                    po_file = os.path.join(self.directory, locale,
                                           'LC_MESSAGES', f"{domain}.po")
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
                        mo_files.append(os.path.join(self.directory, locale,
                                                     'LC_MESSAGES',
                                                     f"{domain}.mo"))
        else:
            po_files.append((self.locale, self.input_file))
            if self.output_file:
                mo_files.append(self.output_file)
            else:
                mo_files.append(os.path.join(self.directory, self.locale,
                                             'LC_MESSAGES',
                                             f"{domain}.mo"))

        if not po_files:
            raise OptionError('no message catalogs found')

        catalogs_and_errors = {}

        for idx, (locale, po_file) in enumerate(po_files):
            mo_file = mo_files[idx]
            with open(po_file, 'rb') as infile:
                catalog = read_po(infile, locale)

            if self.statistics:
                translated = 0
                for message in list(catalog)[1:]:
                    if message.string:
                        translated += 1
                percentage = 0
                if len(catalog):
                    percentage = translated * 100 // len(catalog)
                self.log.info(
                    '%d of %d messages (%d%%) translated in %s',
                    translated, len(catalog), percentage, po_file,
                )

            if catalog.fuzzy and not self.use_fuzzy:
                self.log.info('catalog %s is marked as fuzzy, skipping', po_file)
                continue

            catalogs_and_errors[catalog] = catalog_errors = list(catalog.check())
            for message, errors in catalog_errors:
                for error in errors:
                    self.log.error(
                        'error: %s:%d: %s', po_file, message.lineno, error,
                    )

            self.log.info('compiling catalog %s to %s', po_file, mo_file)

            with open(mo_file, 'wb') as outfile:
                write_mo(outfile, catalog, use_fuzzy=self.use_fuzzy)

        return catalogs_and_errors


def _make_directory_filter(ignore_patterns):
    """
    Build a directory_filter function based on a list of ignore patterns.
    """

    def cli_directory_filter(dirname):
        basename = os.path.basename(dirname)
        return not any(
            fnmatch.fnmatch(basename, ignore_pattern)
            for ignore_pattern
            in ignore_patterns
        )

    return cli_directory_filter


class ExtractMessages(CommandMixin):
    description = 'extract localizable strings from the project code'
    user_options = [
        ('charset=', None,
         'charset to use in the output file (default "utf-8")'),
        ('keywords=', 'k',
         'space-separated list of keywords to look for in addition to the '
         'defaults (may be repeated multiple times)'),
        ('no-default-keywords', None,
         'do not include the default keywords'),
        ('mapping-file=', 'F',
         'path to the mapping configuration file'),
        ('no-location', None,
         'do not include location comments with filename and line number'),
        ('add-location=', None,
         'location lines format. If it is not given or "full", it generates '
         'the lines with both file name and line number. If it is "file", '
         'the line number part is omitted. If it is "never", it completely '
         'suppresses the lines (same as --no-location).'),
        ('omit-header', None,
         'do not include msgid "" entry in header'),
        ('output-file=', 'o',
         'name of the output file'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
        ('sort-output', None,
         'generate sorted output (default False)'),
        ('sort-by-file', None,
         'sort output by file location (default False)'),
        ('msgid-bugs-address=', None,
         'set report address for msgid'),
        ('copyright-holder=', None,
         'set copyright holder in output'),
        ('project=', None,
         'set project name in output'),
        ('version=', None,
         'set project version in output'),
        ('add-comments=', 'c',
         'place comment block with TAG (or those preceding keyword lines) in '
         'output file. Separate multiple TAGs with commas(,)'),  # TODO: Support repetition of this argument
        ('strip-comments', 's',
         'strip the comment TAGs from the comments.'),
        ('input-paths=', None,
         'files or directories that should be scanned for messages. Separate multiple '
         'files or directories with commas(,)'),  # TODO: Support repetition of this argument
        ('input-dirs=', None,  # TODO (3.x): Remove me.
         'alias for input-paths (does allow files as well as directories).'),
        ('ignore-dirs=', None,
         'Patterns for directories to ignore when scanning for messages. '
         'Separate multiple patterns with spaces (default ".* ._")'),
        ('header-comment=', None,
         'header comment for the catalog'),
        ('last-translator=', None,
         'set the name and email of the last translator in output'),
    ]
    boolean_options = [
        'no-default-keywords', 'no-location', 'omit-header', 'no-wrap',
        'sort-output', 'sort-by-file', 'strip-comments',
    ]
    as_args = 'input-paths'
    multiple_value_options = (
        'add-comments',
        'keywords',
        'ignore-dirs',
    )
    option_aliases = {
        'keywords': ('--keyword',),
        'mapping-file': ('--mapping',),
        'output-file': ('--output',),
        'strip-comments': ('--strip-comment-tags',),
        'last-translator': ('--last-translator',),
    }
    option_choices = {
        'add-location': ('full', 'file', 'never'),
    }

    def initialize_options(self):
        self.charset = 'utf-8'
        self.keywords = None
        self.no_default_keywords = False
        self.mapping_file = None
        self.no_location = False
        self.add_location = None
        self.omit_header = False
        self.output_file = None
        self.input_dirs = None
        self.input_paths = None
        self.width = None
        self.no_wrap = False
        self.sort_output = False
        self.sort_by_file = False
        self.msgid_bugs_address = None
        self.copyright_holder = None
        self.project = None
        self.version = None
        self.add_comments = None
        self.strip_comments = False
        self.include_lineno = True
        self.ignore_dirs = None
        self.header_comment = None
        self.last_translator = None

    def finalize_options(self):
        if self.input_dirs:
            if not self.input_paths:
                self.input_paths = self.input_dirs
            else:
                raise OptionError(
                    'input-dirs and input-paths are mutually exclusive',
                )

        keywords = {} if self.no_default_keywords else DEFAULT_KEYWORDS.copy()

        keywords.update(parse_keywords(listify_value(self.keywords)))

        self.keywords = keywords

        if not self.keywords:
            raise OptionError(
                'you must specify new keywords if you disable the default ones',
            )

        if not self.output_file:
            raise OptionError('no output file specified')
        if self.no_wrap and self.width:
            raise OptionError(
                "'--no-wrap' and '--width' are mutually exclusive",
            )
        if not self.no_wrap and not self.width:
            self.width = 76
        elif self.width is not None:
            self.width = int(self.width)

        if self.sort_output and self.sort_by_file:
            raise OptionError(
                "'--sort-output' and '--sort-by-file' are mutually exclusive",
            )

        if self.input_paths:
            if isinstance(self.input_paths, str):
                self.input_paths = re.split(r',\s*', self.input_paths)
        elif self.distribution is not None:
            self.input_paths = dict.fromkeys([
                k.split('.', 1)[0]
                for k in (self.distribution.packages or ())
            ]).keys()
        else:
            self.input_paths = []

        if not self.input_paths:
            raise OptionError("no input files or directories specified")

        for path in self.input_paths:
            if not os.path.exists(path):
                raise OptionError(f"Input path: {path} does not exist")

        self.add_comments = listify_value(self.add_comments or (), ",")

        if self.distribution:
            if not self.project:
                self.project = self.distribution.get_name()
            if not self.version:
                self.version = self.distribution.get_version()

        if self.add_location == 'never':
            self.no_location = True
        elif self.add_location == 'file':
            self.include_lineno = False

        ignore_dirs = listify_value(self.ignore_dirs)
        if ignore_dirs:
            self.directory_filter = _make_directory_filter(self.ignore_dirs)
        else:
            self.directory_filter = None

    def _build_callback(self, path: str):
        def callback(filename: str, method: str, options: dict):
            if method == 'ignore':
                return

            # If we explicitly provide a full filepath, just use that.
            # Otherwise, path will be the directory path and filename
            # is the relative path from that dir to the file.
            # So we can join those to get the full filepath.
            if os.path.isfile(path):
                filepath = path
            else:
                filepath = os.path.normpath(os.path.join(path, filename))

            optstr = ''
            if options:
                opt_values = ", ".join(f'{k}="{v}"' for k, v in options.items())
                optstr = f" ({opt_values})"
            self.log.info('extracting messages from %s%s', filepath, optstr)

        return callback

    def run(self):
        mappings = self._get_mappings()
        with open(self.output_file, 'wb') as outfile:
            catalog = Catalog(project=self.project,
                              version=self.version,
                              msgid_bugs_address=self.msgid_bugs_address,
                              copyright_holder=self.copyright_holder,
                              charset=self.charset,
                              header_comment=(self.header_comment or DEFAULT_HEADER),
                              last_translator=self.last_translator)

            for path, method_map, options_map in mappings:
                callback = self._build_callback(path)
                if os.path.isfile(path):
                    current_dir = os.getcwd()
                    extracted = check_and_call_extract_file(
                        path, method_map, options_map,
                        callback, self.keywords, self.add_comments,
                        self.strip_comments, current_dir,
                    )
                else:
                    extracted = extract_from_dir(
                        path, method_map, options_map,
                        keywords=self.keywords,
                        comment_tags=self.add_comments,
                        callback=callback,
                        strip_comment_tags=self.strip_comments,
                        directory_filter=self.directory_filter,
                    )
                for filename, lineno, message, comments, context in extracted:
                    if os.path.isfile(path):
                        filepath = filename  # already normalized
                    else:
                        filepath = os.path.normpath(os.path.join(path, filename))

                    catalog.add(message, None, [(filepath, lineno)],
                                auto_comments=comments, context=context)

            self.log.info('writing PO template file to %s', self.output_file)
            write_po(outfile, catalog, width=self.width,
                     no_location=self.no_location,
                     omit_header=self.omit_header,
                     sort_output=self.sort_output,
                     sort_by_file=self.sort_by_file,
                     include_lineno=self.include_lineno)

    def _get_mappings(self):
        mappings = []

        if self.mapping_file:
            with open(self.mapping_file) as fileobj:
                method_map, options_map = parse_mapping(fileobj)
            for path in self.input_paths:
                mappings.append((path, method_map, options_map))

        elif getattr(self.distribution, 'message_extractors', None):
            message_extractors = self.distribution.message_extractors
            for path, mapping in message_extractors.items():
                if isinstance(mapping, str):
                    method_map, options_map = parse_mapping(StringIO(mapping))
                else:
                    method_map, options_map = [], {}
                    for pattern, method, options in mapping:
                        method_map.append((pattern, method))
                        options_map[pattern] = options or {}
                mappings.append((path, method_map, options_map))

        else:
            for path in self.input_paths:
                mappings.append((path, DEFAULT_MAPPING, {}))

        return mappings


class InitCatalog(CommandMixin):
    description = 'create a new catalog based on a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to output directory'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('locale=', 'l',
         'locale for the new localized catalog'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
    ]
    boolean_options = ['no-wrap']

    def initialize_options(self):
        self.output_dir = None
        self.output_file = None
        self.input_file = None
        self.locale = None
        self.domain = 'messages'
        self.no_wrap = False
        self.width = None

    def finalize_options(self):
        if not self.input_file:
            raise OptionError('you must specify the input file')

        if not self.locale:
            raise OptionError('you must provide a locale for the new catalog')
        try:
            self._locale = Locale.parse(self.locale)
        except UnknownLocaleError as e:
            raise OptionError(e) from e

        if not self.output_file and not self.output_dir:
            raise OptionError('you must specify the output directory')
        if not self.output_file:
            self.output_file = os.path.join(self.output_dir, self.locale,
                                            'LC_MESSAGES', f"{self.domain}.po")

        if not os.path.exists(os.path.dirname(self.output_file)):
            os.makedirs(os.path.dirname(self.output_file))
        if self.no_wrap and self.width:
            raise OptionError("'--no-wrap' and '--width' are mutually exclusive")
        if not self.no_wrap and not self.width:
            self.width = 76
        elif self.width is not None:
            self.width = int(self.width)

    def run(self):
        self.log.info(
            'creating catalog %s based on %s', self.output_file, self.input_file,
        )

        with open(self.input_file, 'rb') as infile:
            # Although reading from the catalog template, read_po must be fed
            # the locale in order to correctly calculate plurals
            catalog = read_po(infile, locale=self.locale)

        catalog.locale = self._locale
        catalog.revision_date = datetime.datetime.now(LOCALTZ)
        catalog.fuzzy = False

        with open(self.output_file, 'wb') as outfile:
            write_po(outfile, catalog, width=self.width)


class UpdateCatalog(CommandMixin):
    description = 'update message catalogs from a POT file'
    user_options = [
        ('domain=', 'D',
         "domain of PO file (default 'messages')"),
        ('input-file=', 'i',
         'name of the input file'),
        ('output-dir=', 'd',
         'path to base directory containing the catalogs'),
        ('output-file=', 'o',
         "name of the output file (default "
         "'<output_dir>/<locale>/LC_MESSAGES/<domain>.po')"),
        ('omit-header', None,
         "do not include msgid "" entry in header"),
        ('locale=', 'l',
         'locale of the catalog to compile'),
        ('width=', 'w',
         'set output line width (default 76)'),
        ('no-wrap', None,
         'do not break long message lines, longer than the output line width, '
         'into several lines'),
        ('ignore-obsolete=', None,
         'whether to omit obsolete messages from the output'),
        ('init-missing=', None,
         'if any output files are missing, initialize them first'),
        ('no-fuzzy-matching', 'N',
         'do not use fuzzy matching'),
        ('update-header-comment', None,
         'update target header comment'),
        ('previous', None,
         'keep previous msgids of translated messages'),
        ('check=', None,
         'don\'t update the catalog, just return the status. Return code 0 '
         'means nothing would change. Return code 1 means that the catalog '
         'would be updated'),
        ('ignore-pot-creation-date=', None,
         'ignore changes to POT-Creation-Date when updating or checking'),
    ]
    boolean_options = [
        'omit-header', 'no-wrap', 'ignore-obsolete', 'init-missing',
        'no-fuzzy-matching', 'previous', 'update-header-comment',
        'check', 'ignore-pot-creation-date',
    ]

    def initialize_options(self):
        self.domain = 'messages'
        self.input_file = None
        self.output_dir = None
        self.output_file = None
        self.omit_header = False
        self.locale = None
        self.width = None
        self.no_wrap = False
        self.ignore_obsolete = False
        self.init_missing = False
        self.no_fuzzy_matching = False
        self.update_header_comment = False
        self.previous = False
        self.check = False
        self.ignore_pot_creation_date = False

    def finalize_options(self):
        if not self.input_file:
            raise OptionError('you must specify the input file')
        if not self.output_file and not self.output_dir:
            raise OptionError('you must specify the output file or directory')
        if self.output_file and not self.locale:
            raise OptionError('you must specify the locale')

        if self.init_missing:
            if not self.locale:
                raise OptionError(
                    'you must specify the locale for '
                    'the init-missing option to work',
                )

            try:
                self._locale = Locale.parse(self.locale)
            except UnknownLocaleError as e:
                raise OptionError(e) from e
        else:
            self._locale = None

        if self.no_wrap and self.width:
            raise OptionError("'--no-wrap' and '--width' are mutually exclusive")
        if not self.no_wrap and not self.width:
            self.width = 76
        elif self.width is not None:
            self.width = int(self.width)
        if self.no_fuzzy_matching and self.previous:
            self.previous = False

    def run(self):
        check_status = {}
        po_files = []
        if not self.output_file:
            if self.locale:
                po_files.append((self.locale,
                                 os.path.join(self.output_dir, self.locale,
                                              'LC_MESSAGES',
                                              f"{self.domain}.po")))
            else:
                for locale in os.listdir(self.output_dir):
                    po_file = os.path.join(self.output_dir, locale,
                                           'LC_MESSAGES',
                                           f"{self.domain}.po")
                    if os.path.exists(po_file):
                        po_files.append((locale, po_file))
        else:
            po_files.append((self.locale, self.output_file))

        if not po_files:
            raise OptionError('no message catalogs found')

        domain = self.domain
        if not domain:
            domain = os.path.splitext(os.path.basename(self.input_file))[0]

        with open(self.input_file, 'rb') as infile:
            template = read_po(infile)

        for locale, filename in po_files:
            if self.init_missing and not os.path.exists(filename):
                if self.check:
                    check_status[filename] = False
                    continue
                self.log.info(
                    'creating catalog %s based on %s', filename, self.input_file,
                )

                with open(self.input_file, 'rb') as infile:
                    # Although reading from the catalog template, read_po must
                    # be fed the locale in order to correctly calculate plurals
                    catalog = read_po(infile, locale=self.locale)

                catalog.locale = self._locale
                catalog.revision_date = datetime.datetime.now(LOCALTZ)
                catalog.fuzzy = False

                with open(filename, 'wb') as outfile:
                    write_po(outfile, catalog)

            self.log.info('updating catalog %s based on %s', filename, self.input_file)
            with open(filename, 'rb') as infile:
                catalog = read_po(infile, locale=locale, domain=domain)

            catalog.update(
                template, self.no_fuzzy_matching,
                update_header_comment=self.update_header_comment,
                update_creation_date=not self.ignore_pot_creation_date,
            )

            tmpname = os.path.join(os.path.dirname(filename),
                                   tempfile.gettempprefix() +
                                   os.path.basename(filename))
            try:
                with open(tmpname, 'wb') as tmpfile:
                    write_po(tmpfile, catalog,
                             omit_header=self.omit_header,
                             ignore_obsolete=self.ignore_obsolete,
                             include_previous=self.previous, width=self.width)
            except Exception:
                os.remove(tmpname)
                raise

            if self.check:
                with open(filename, "rb") as origfile:
                    original_catalog = read_po(origfile)
                with open(tmpname, "rb") as newfile:
                    updated_catalog = read_po(newfile)
                updated_catalog.revision_date = original_catalog.revision_date
                check_status[filename] = updated_catalog.is_identical(original_catalog)
                os.remove(tmpname)
                continue

            try:
                os.rename(tmpname, filename)
            except OSError:
                # We're probably on Windows, which doesn't support atomic
                # renames, at least not through Python
                # If the error is in fact due to a permissions problem, that
                # same error is going to be raised from one of the following
                # operations
                os.remove(filename)
                shutil.copy(tmpname, filename)
                os.remove(tmpname)

        if self.check:
            for filename, up_to_date in check_status.items():
                if up_to_date:
                    self.log.info('Catalog %s is up to date.', filename)
                else:
                    self.log.warning('Catalog %s is out of date.', filename)
            if not all(check_status.values()):
                raise BaseError("Some catalogs are out of date.")
            else:
                self.log.info("All the catalogs are up-to-date.")
            return


class CommandLineInterface:
    """Command-line interface.

    This class provides a simple command-line interface to the message
    extraction and PO file generation functionality.
    """

    usage = '%%prog %s [options] %s'
    version = f'%prog {VERSION}'
    commands = {
        'compile': 'compile message catalogs to MO files',
        'extract': 'extract messages from source files and generate a POT file',
        'init': 'create new message catalogs from a POT file',
        'update': 'update existing message catalogs from a POT file',
    }

    command_classes = {
        'compile': CompileCatalog,
        'extract': ExtractMessages,
        'init': InitCatalog,
        'update': UpdateCatalog,
    }

    log = None  # Replaced on instance level

    def run(self, argv=None):
        """Main entry point of the command-line interface.

        :param argv: list of arguments passed on the command-line
        """

        if argv is None:
            argv = sys.argv

        self.parser = optparse.OptionParser(usage=self.usage % ('command', '[args]'),
                                            version=self.version)
        self.parser.disable_interspersed_args()
        self.parser.print_help = self._help
        self.parser.add_option('--list-locales', dest='list_locales',
                               action='store_true',
                               help="print all known locales and exit")
        self.parser.add_option('-v', '--verbose', action='store_const',
                               dest='loglevel', const=logging.DEBUG,
                               help='print as much as possible')
        self.parser.add_option('-q', '--quiet', action='store_const',
                               dest='loglevel', const=logging.ERROR,
                               help='print as little as possible')
        self.parser.set_defaults(list_locales=False, loglevel=logging.INFO)

        options, args = self.parser.parse_args(argv[1:])

        self._configure_logging(options.loglevel)
        if options.list_locales:
            identifiers = localedata.locale_identifiers()
            id_width = max(len(identifier) for identifier in identifiers) + 1
            for identifier in sorted(identifiers):
                locale = Locale.parse(identifier)
                print(f"{identifier:<{id_width}} {locale.english_name}")
            return 0

        if not args:
            self.parser.error('no valid command or option passed. '
                              'Try the -h/--help option for more information.')

        cmdname = args[0]
        if cmdname not in self.commands:
            self.parser.error(f'unknown command "{cmdname}"')

        cmdinst = self._configure_command(cmdname, args[1:])
        return cmdinst.run()

    def _configure_logging(self, loglevel):
        self.log = log
        self.log.setLevel(loglevel)
        # Don't add a new handler for every instance initialization (#227), this
        # would cause duplicated output when the CommandLineInterface as an
        # normal Python class.
        if self.log.handlers:
            handler = self.log.handlers[0]
        else:
            handler = logging.StreamHandler()
            self.log.addHandler(handler)
        handler.setLevel(loglevel)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

    def _help(self):
        print(self.parser.format_help())
        print("commands:")
        cmd_width = max(8, max(len(command) for command in self.commands) + 1)
        for name, description in sorted(self.commands.items()):
            print(f"  {name:<{cmd_width}} {description}")

    def _configure_command(self, cmdname, argv):
        """
        :type cmdname: str
        :type argv: list[str]
        """
        cmdclass = self.command_classes[cmdname]
        cmdinst = cmdclass()
        if self.log:
            cmdinst.log = self.log  # Use our logger, not distutils'.
        assert isinstance(cmdinst, CommandMixin)
        cmdinst.initialize_options()

        parser = optparse.OptionParser(
            usage=self.usage % (cmdname, ''),
            description=self.commands[cmdname],
        )
        as_args = getattr(cmdclass, "as_args", ())
        for long, short, help in cmdclass.user_options:
            name = long.strip("=")
            default = getattr(cmdinst, name.replace("-", "_"))
            strs = [f"--{name}"]
            if short:
                strs.append(f"-{short}")
            strs.extend(cmdclass.option_aliases.get(name, ()))
            choices = cmdclass.option_choices.get(name, None)
            if name == as_args:
                parser.usage += f"<{name}>"
            elif name in cmdclass.boolean_options:
                parser.add_option(*strs, action="store_true", help=help)
            elif name in cmdclass.multiple_value_options:
                parser.add_option(*strs, action="append", help=help, choices=choices)
            else:
                parser.add_option(*strs, help=help, default=default, choices=choices)
        options, args = parser.parse_args(argv)

        if as_args:
            setattr(options, as_args.replace('-', '_'), args)

        for key, value in vars(options).items():
            setattr(cmdinst, key, value)

        try:
            cmdinst.ensure_finalized()
        except OptionError as err:
            parser.error(str(err))

        return cmdinst


def main():
    return CommandLineInterface().run(sys.argv)


def parse_mapping(fileobj, filename=None):
    """Parse an extraction method mapping from a file-like object.

    >>> buf = StringIO('''
    ... [extractors]
    ... custom = mypackage.module:myfunc
    ...
    ... # Python source files
    ... [python: **.py]
    ...
    ... # Genshi templates
    ... [genshi: **/templates/**.html]
    ... include_attrs =
    ... [genshi: **/templates/**.txt]
    ... template_class = genshi.template:TextTemplate
    ... encoding = latin-1
    ...
    ... # Some custom extractor
    ... [custom: **/custom/*.*]
    ... ''')

    >>> method_map, options_map = parse_mapping(buf)
    >>> len(method_map)
    4

    >>> method_map[0]
    ('**.py', 'python')
    >>> options_map['**.py']
    {}
    >>> method_map[1]
    ('**/templates/**.html', 'genshi')
    >>> options_map['**/templates/**.html']['include_attrs']
    ''
    >>> method_map[2]
    ('**/templates/**.txt', 'genshi')
    >>> options_map['**/templates/**.txt']['template_class']
    'genshi.template:TextTemplate'
    >>> options_map['**/templates/**.txt']['encoding']
    'latin-1'

    >>> method_map[3]
    ('**/custom/*.*', 'mypackage.module:myfunc')
    >>> options_map['**/custom/*.*']
    {}

    :param fileobj: a readable file-like object containing the configuration
                    text to parse
    :see: `extract_from_directory`
    """
    extractors = {}
    method_map = []
    options_map = {}

    parser = RawConfigParser()
    parser._sections = OrderedDict(parser._sections)  # We need ordered sections
    parser.read_file(fileobj, filename)

    for section in parser.sections():
        if section == 'extractors':
            extractors = dict(parser.items(section))
        else:
            method, pattern = (part.strip() for part in section.split(':', 1))
            method_map.append((pattern, method))
            options_map[pattern] = dict(parser.items(section))

    if extractors:
        for idx, (pattern, method) in enumerate(method_map):
            if method in extractors:
                method = extractors[method]
            method_map[idx] = (pattern, method)

    return method_map, options_map


def _parse_spec(s: str) -> tuple[int | None, tuple[int | tuple[int, str], ...]]:
    inds = []
    number = None
    for x in s.split(','):
        if x[-1] == 't':
            number = int(x[:-1])
        elif x[-1] == 'c':
            inds.append((int(x[:-1]), 'c'))
        else:
            inds.append(int(x))
    return number, tuple(inds)


def parse_keywords(strings: Iterable[str] = ()):
    """Parse keywords specifications from the given list of strings.

    >>> import pprint
    >>> keywords = ['_', 'dgettext:2', 'dngettext:2,3', 'pgettext:1c,2',
    ...             'polymorphic:1', 'polymorphic:2,2t', 'polymorphic:3c,3t']
    >>> pprint.pprint(parse_keywords(keywords))
    {'_': None,
     'dgettext': (2,),
     'dngettext': (2, 3),
     'pgettext': ((1, 'c'), 2),
     'polymorphic': {None: (1,), 2: (2,), 3: ((3, 'c'),)}}

    The input keywords are in GNU Gettext style; see :doc:`cmdline` for details.

    The output is a dictionary mapping keyword names to a dictionary of specifications.
    Keys in this dictionary are numbers of arguments, where ``None`` means that all numbers
    of arguments are matched, and a number means only calls with that number of arguments
    are matched (which happens when using the "t" specifier). However, as a special
    case for backwards compatibility, if the dictionary of specifications would
    be ``{None: x}``, i.e., there is only one specification and it matches all argument
    counts, then it is collapsed into just ``x``.

    A specification is either a tuple or None. If a tuple, each element can be either a number
    ``n``, meaning that the nth argument should be extracted as a message, or the tuple
    ``(n, 'c')``, meaning that the nth argument should be extracted as context for the
    messages. A ``None`` specification is equivalent to ``(1,)``, extracting the first
    argument.
    """
    keywords = {}
    for string in strings:
        if ':' in string:
            funcname, spec_str = string.split(':')
            number, spec = _parse_spec(spec_str)
        else:
            funcname = string
            number = None
            spec = None
        keywords.setdefault(funcname, {})[number] = spec

    # For best backwards compatibility, collapse {None: x} into x.
    for k, v in keywords.items():
        if set(v) == {None}:
            keywords[k] = v[None]

    return keywords


def __getattr__(name: str):
    # Re-exports for backwards compatibility;
    # `setuptools_frontend` is the canonical import location.
    if name in {'check_message_extractors', 'compile_catalog', 'extract_messages', 'init_catalog', 'update_catalog'}:
        from babel.messages import setuptools_frontend

        return getattr(setuptools_frontend, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == '__main__':
    main()
