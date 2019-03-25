# -*- coding: utf-8 -*-
"""
    sphinx.util
    ~~~~~~~~~~~

    Utility functions for Sphinx.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import absolute_import

import fnmatch
import os
import posixpath
import re
import sys
import tempfile
import traceback
import unicodedata
import warnings
from codecs import BOM_UTF8
from collections import deque
from datetime import datetime
from hashlib import md5
from os import path
from time import mktime, strptime

from docutils.utils import relative_path
from six import text_type, binary_type, itervalues
from six.moves import range
from six.moves.urllib.parse import urlsplit, urlunsplit, quote_plus, parse_qsl, urlencode

from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.errors import PycodeError, SphinxParallelError, ExtensionError
from sphinx.util import logging
from sphinx.util.console import strip_colors, colorize, bold, term_width_line  # type: ignore
from sphinx.util.fileutil import copy_asset_file
from sphinx.util.osutil import fs_encoding
from sphinx.util import smartypants  # noqa

# import other utilities; partly for backwards compatibility, so don't
# prune unused ones indiscriminately
from sphinx.util.osutil import (  # noqa
    SEP, os_path, relative_uri, ensuredir, walk, mtimes_of_files, movefile,
    copyfile, copytimes, make_filename, ustrftime)
from sphinx.util.nodes import (   # noqa
    nested_parse_with_titles, split_explicit_title, explicit_title_re,
    caption_ref_re)
from sphinx.util.matching import patfilter  # noqa

if False:
    # For type annotation
    from typing import Any, Callable, Dict, IO, Iterable, Iterator, List, Pattern, Sequence, Set, Tuple, Union  # NOQA


logger = logging.getLogger(__name__)

# Generally useful regular expressions.
ws_re = re.compile(r'\s+')                      # type: Pattern
url_re = re.compile(r'(?P<schema>.+)://.*')     # type: Pattern


# High-level utility functions.

def docname_join(basedocname, docname):
    # type: (unicode, unicode) -> unicode
    return posixpath.normpath(
        posixpath.join('/' + basedocname, '..', docname))[1:]


def path_stabilize(filepath):
    # type: (unicode) -> unicode
    "normalize path separater and unicode string"
    newpath = filepath.replace(os.path.sep, SEP)
    if isinstance(newpath, text_type):
        newpath = unicodedata.normalize('NFC', newpath)
    return newpath


def get_matching_files(dirname, exclude_matchers=()):
    # type: (unicode, Tuple[Callable[[unicode], bool], ...]) -> Iterable[unicode]
    """Get all file names in a directory, recursively.

    Exclude files and dirs matching some matcher in *exclude_matchers*.
    """
    # dirname is a normalized absolute path.
    dirname = path.normpath(path.abspath(dirname))
    dirlen = len(dirname) + 1    # exclude final os.path.sep

    for root, dirs, files in walk(dirname, followlinks=True):
        relativeroot = root[dirlen:]

        qdirs = enumerate(path_stabilize(path.join(relativeroot, dn))
                          for dn in dirs)  # type: Iterable[Tuple[int, unicode]]
        qfiles = enumerate(path_stabilize(path.join(relativeroot, fn))
                           for fn in files)  # type: Iterable[Tuple[int, unicode]]
        for matcher in exclude_matchers:
            qdirs = [entry for entry in qdirs if not matcher(entry[1])]
            qfiles = [entry for entry in qfiles if not matcher(entry[1])]

        dirs[:] = sorted(dirs[i] for (i, _) in qdirs)

        for i, filename in sorted(qfiles):
            yield filename


def get_matching_docs(dirname, suffixes, exclude_matchers=()):
    # type: (unicode, List[unicode], Tuple[Callable[[unicode], bool], ...]) -> Iterable[unicode]  # NOQA
    """Get all file names (without suffixes) matching a suffix in a directory,
    recursively.

    Exclude files and dirs matching a pattern in *exclude_patterns*.
    """
    suffixpatterns = ['*' + s for s in suffixes]
    for filename in get_matching_files(dirname, exclude_matchers):
        for suffixpattern in suffixpatterns:
            if fnmatch.fnmatch(filename, suffixpattern):
                yield filename[:-len(suffixpattern) + 1]
                break


class FilenameUniqDict(dict):
    """
    A dictionary that automatically generates unique names for its keys,
    interpreted as filenames, and keeps track of a set of docnames they
    appear in.  Used for images and downloadable files in the environment.
    """
    def __init__(self):
        # type: () -> None
        self._existing = set()  # type: Set[unicode]

    def add_file(self, docname, newfile):
        # type: (unicode, unicode) -> unicode
        if newfile in self:
            self[newfile][0].add(docname)
            return self[newfile][1]
        uniquename = path.basename(newfile)
        base, ext = path.splitext(uniquename)
        i = 0
        while uniquename in self._existing:
            i += 1
            uniquename = '%s%s%s' % (base, i, ext)
        self[newfile] = (set([docname]), uniquename)
        self._existing.add(uniquename)
        return uniquename

    def purge_doc(self, docname):
        # type: (unicode) -> None
        for filename, (docs, unique) in list(self.items()):
            docs.discard(docname)
            if not docs:
                del self[filename]
                self._existing.discard(unique)

    def merge_other(self, docnames, other):
        # type: (Set[unicode], Dict[unicode, Tuple[Set[unicode], Any]]) -> None
        for filename, (docs, unique) in other.items():
            for doc in docs & set(docnames):
                self.add_file(doc, filename)

    def __getstate__(self):
        # type: () -> Set[unicode]
        return self._existing

    def __setstate__(self, state):
        # type: (Set[unicode]) -> None
        self._existing = state


class DownloadFiles(dict):
    """A special dictionary for download files.

    .. important:: This class would be refactored in nearly future.
                   Hence don't hack this directly.
    """

    def add_file(self, docname, filename):
        # type: (unicode, unicode) -> None
        if filename not in self:
            digest = md5(filename.encode('utf-8')).hexdigest()
            dest = '%s/%s' % (digest, os.path.basename(filename))
            self[filename] = (set(), dest)

        self[filename][0].add(docname)
        return self[filename][1]

    def purge_doc(self, docname):
        # type: (unicode) -> None
        for filename, (docs, dest) in list(self.items()):
            docs.discard(docname)
            if not docs:
                del self[filename]

    def merge_other(self, docnames, other):
        # type: (Set[unicode], Dict[unicode, Tuple[Set[unicode], Any]]) -> None
        for filename, (docs, dest) in other.items():
            for docname in docs & set(docnames):
                self.add_file(docname, filename)


def copy_static_entry(source, targetdir, builder, context={},
                      exclude_matchers=(), level=0):
    # type: (unicode, unicode, Any, Dict, Tuple[Callable, ...], int) -> None
    """[DEPRECATED] Copy a HTML builder static_path entry from source to targetdir.

    Handles all possible cases of files, directories and subdirectories.
    """
    warnings.warn('sphinx.util.copy_static_entry is deprecated for removal',
                  RemovedInSphinx30Warning, stacklevel=2)

    if exclude_matchers:
        relpath = relative_path(path.join(builder.srcdir, 'dummy'), source)
        for matcher in exclude_matchers:
            if matcher(relpath):
                return
    if path.isfile(source):
        copy_asset_file(source, targetdir, context, builder.templates)
    elif path.isdir(source):
        if not path.isdir(targetdir):
            os.mkdir(targetdir)
        for entry in os.listdir(source):
            if entry.startswith('.'):
                continue
            newtarget = targetdir
            if path.isdir(path.join(source, entry)):
                newtarget = path.join(targetdir, entry)
            copy_static_entry(path.join(source, entry), newtarget,
                              builder, context, level=level + 1,
                              exclude_matchers=exclude_matchers)


_DEBUG_HEADER = '''\
# Sphinx version: %s
# Python version: %s (%s)
# Docutils version: %s %s
# Jinja2 version: %s
# Last messages:
%s
# Loaded extensions:
'''


def save_traceback(app):
    # type: (Any) -> unicode
    """Save the current exception's traceback in a temporary file."""
    import sphinx
    import jinja2
    import docutils
    import platform
    exc = sys.exc_info()[1]
    if isinstance(exc, SphinxParallelError):
        exc_format = '(Error in parallel process)\n' + exc.traceback
    else:
        exc_format = traceback.format_exc()
    fd, path = tempfile.mkstemp('.log', 'sphinx-err-')
    last_msgs = ''
    if app is not None:
        last_msgs = '\n'.join(
            '#   %s' % strip_colors(force_decode(s, 'utf-8')).strip()  # type: ignore
            for s in app.messagelog)
    os.write(fd, (_DEBUG_HEADER %
                  (sphinx.__display_version__,
                   platform.python_version(),
                   platform.python_implementation(),
                   docutils.__version__, docutils.__version_details__,
                   jinja2.__version__,  # type: ignore
                   last_msgs)).encode('utf-8'))
    if app is not None:
        for ext in itervalues(app.extensions):
            modfile = getattr(ext.module, '__file__', 'unknown')
            if isinstance(modfile, bytes):
                modfile = modfile.decode(fs_encoding, 'replace')
            if ext.version != 'builtin':
                os.write(fd, ('#   %s (%s) from %s\n' %
                              (ext.name, ext.version, modfile)).encode('utf-8'))
    os.write(fd, exc_format.encode('utf-8'))
    os.close(fd)
    return path


def get_module_source(modname):
    # type: (str) -> Tuple[unicode, unicode]
    """Try to find the source code for a module.

    Can return ('file', 'filename') in which case the source is in the given
    file, or ('string', 'source') which which case the source is the string.
    """
    if modname not in sys.modules:
        try:
            __import__(modname)
        except Exception as err:
            raise PycodeError('error importing %r' % modname, err)
    mod = sys.modules[modname]
    filename = getattr(mod, '__file__', None)
    loader = getattr(mod, '__loader__', None)
    if loader and getattr(loader, 'get_filename', None):
        try:
            filename = loader.get_filename(modname)
        except Exception as err:
            raise PycodeError('error getting filename for %r' % filename, err)
    if filename is None and loader:
        try:
            filename = loader.get_source(modname)
            if filename:
                return 'string', filename
        except Exception as err:
            raise PycodeError('error getting source for %r' % modname, err)
    if filename is None:
        raise PycodeError('no source found for module %r' % modname)
    filename = path.normpath(path.abspath(filename))
    lfilename = filename.lower()
    if lfilename.endswith('.pyo') or lfilename.endswith('.pyc'):
        filename = filename[:-1]
        if not path.isfile(filename) and path.isfile(filename + 'w'):
            filename += 'w'
    elif not (lfilename.endswith('.py') or lfilename.endswith('.pyw')):
        raise PycodeError('source is not a .py file: %r' % filename)
    elif ('.egg' + os.path.sep) in filename:
        pat = '(?<=\\.egg)' + re.escape(os.path.sep)
        eggpath, _ = re.split(pat, filename, 1)
        if path.isfile(eggpath):
            return 'file', filename

    if not path.isfile(filename):
        raise PycodeError('source file is not present: %r' % filename)
    return 'file', filename


def get_full_modname(modname, attribute):
    # type: (str, unicode) -> unicode
    if modname is None:
        # Prevents a TypeError: if the last getattr() call will return None
        # then it's better to return it directly
        return None
    __import__(modname)
    module = sys.modules[modname]

    # Allow an attribute to have multiple parts and incidentially allow
    # repeated .s in the attribute.
    value = module
    for attr in attribute.split('.'):
        if attr:
            value = getattr(value, attr)

    return getattr(value, '__module__', None)


# a regex to recognize coding cookies
_coding_re = re.compile(r'coding[:=]\s*([-\w.]+)')


def detect_encoding(readline):
    # type: (Callable) -> unicode
    """Like tokenize.detect_encoding() from Py3k, but a bit simplified."""

    def read_or_stop():
        # type: () -> unicode
        try:
            return readline()
        except StopIteration:
            return None

    def get_normal_name(orig_enc):
        # type: (str) -> str
        """Imitates get_normal_name in tokenizer.c."""
        # Only care about the first 12 characters.
        enc = orig_enc[:12].lower().replace('_', '-')
        if enc == 'utf-8' or enc.startswith('utf-8-'):
            return 'utf-8'
        if enc in ('latin-1', 'iso-8859-1', 'iso-latin-1') or \
           enc.startswith(('latin-1-', 'iso-8859-1-', 'iso-latin-1-')):
            return 'iso-8859-1'
        return orig_enc

    def find_cookie(line):
        # type: (unicode) -> unicode
        try:
            line_string = line.decode('ascii')
        except UnicodeDecodeError:
            return None

        matches = _coding_re.findall(line_string)
        if not matches:
            return None
        return get_normal_name(matches[0])

    default = sys.getdefaultencoding()
    first = read_or_stop()
    if first and first.startswith(BOM_UTF8):
        first = first[3:]
        default = 'utf-8-sig'
    if not first:
        return default
    encoding = find_cookie(first)
    if encoding:
        return encoding
    second = read_or_stop()
    if not second:
        return default
    encoding = find_cookie(second)
    if encoding:
        return encoding
    return default


# Low-level utility functions and classes.

class Tee(object):
    """
    File-like object writing to two streams.
    """
    def __init__(self, stream1, stream2):
        # type: (IO, IO) -> None
        self.stream1 = stream1
        self.stream2 = stream2

    def write(self, text):
        # type: (unicode) -> None
        self.stream1.write(text)
        self.stream2.write(text)

    def flush(self):
        # type: () -> None
        if hasattr(self.stream1, 'flush'):
            self.stream1.flush()
        if hasattr(self.stream2, 'flush'):
            self.stream2.flush()


def parselinenos(spec, total):
    # type: (unicode, int) -> List[int]
    """Parse a line number spec (such as "1,2,4-6") and return a list of
    wanted line numbers.
    """
    items = list()
    parts = spec.split(',')
    for part in parts:
        try:
            begend = part.strip().split('-')
            if ['', ''] == begend:
                raise ValueError
            elif len(begend) == 1:
                items.append(int(begend[0]) - 1)
            elif len(begend) == 2:
                start = int(begend[0] or 1)  # left half open (cf. -10)
                end = int(begend[1] or max(start, total))  # right half open (cf. 10-)
                if start > end:  # invalid range (cf. 10-1)
                    raise ValueError
                items.extend(range(start - 1, end))
            else:
                raise ValueError
        except Exception:
            raise ValueError('invalid line number spec: %r' % spec)

    return items


def force_decode(string, encoding):
    # type: (unicode, unicode) -> unicode
    """Forcibly get a unicode string out of a bytestring."""
    if isinstance(string, binary_type):
        try:
            if encoding:
                string = string.decode(encoding)
            else:
                # try decoding with utf-8, should only work for real UTF-8
                string = string.decode('utf-8')
        except UnicodeError:
            # last resort -- can't fail
            string = string.decode('latin1')
    return string


class attrdict(dict):
    def __getattr__(self, key):
        # type: (unicode) -> unicode
        return self[key]

    def __setattr__(self, key, val):
        # type: (unicode, unicode) -> None
        self[key] = val

    def __delattr__(self, key):
        # type: (unicode) -> None
        del self[key]


def rpartition(s, t):
    # type: (unicode, unicode) -> Tuple[unicode, unicode]
    """Similar to str.rpartition from 2.5, but doesn't return the separator."""
    i = s.rfind(t)
    if i != -1:
        return s[:i], s[i + len(t):]
    return '', s


def split_into(n, type, value):
    # type: (int, unicode, unicode) -> List[unicode]
    """Split an index entry into a given number of parts at semicolons."""
    parts = [x.strip() for x in value.split(';', n - 1)]
    if sum(1 for part in parts if part) < n:
        raise ValueError('invalid %s index entry %r' % (type, value))
    return parts


def split_index_msg(type, value):
    # type: (unicode, unicode) -> List[unicode]
    # new entry types must be listed in directives/other.py!
    if type == 'single':
        try:
            result = split_into(2, 'single', value)
        except ValueError:
            result = split_into(1, 'single', value)
    elif type == 'pair':
        result = split_into(2, 'pair', value)
    elif type == 'triple':
        result = split_into(3, 'triple', value)
    elif type == 'see':
        result = split_into(2, 'see', value)
    elif type == 'seealso':
        result = split_into(2, 'see', value)
    else:
        raise ValueError('invalid %s index entry %r' % (type, value))

    return result


def format_exception_cut_frames(x=1):
    # type: (int) -> unicode
    """Format an exception with traceback, but only the last x frames."""
    typ, val, tb = sys.exc_info()
    # res = ['Traceback (most recent call last):\n']
    res = []  # type: List[unicode]
    tbres = traceback.format_tb(tb)
    res += tbres[-x:]
    res += traceback.format_exception_only(typ, val)
    return ''.join(res)


class PeekableIterator(object):
    """
    An iterator which wraps any iterable and makes it possible to peek to see
    what's the next item.
    """
    def __init__(self, iterable):
        # type: (Iterable) -> None
        self.remaining = deque()  # type: deque
        self._iterator = iter(iterable)

    def __iter__(self):
        # type: () -> PeekableIterator
        return self

    def __next__(self):
        # type: () -> Any
        """Return the next item from the iterator."""
        if self.remaining:
            return self.remaining.popleft()
        return next(self._iterator)

    next = __next__  # Python 2 compatibility

    def push(self, item):
        # type: (Any) -> None
        """Push the `item` on the internal stack, it will be returned on the
        next :meth:`next` call.
        """
        self.remaining.append(item)

    def peek(self):
        # type: () -> Any
        """Return the next item without changing the state of the iterator."""
        item = next(self)
        self.push(item)
        return item


def import_object(objname, source=None):
    # type: (str, unicode) -> Any
    try:
        module, name = objname.rsplit('.', 1)
    except ValueError as err:
        raise ExtensionError('Invalid full object name %s' % objname +
                             (source and ' (needed for %s)' % source or ''),
                             err)
    try:
        return getattr(__import__(module, None, None, [name]), name)
    except ImportError as err:
        raise ExtensionError('Could not import %s' % module +
                             (source and ' (needed for %s)' % source or ''),
                             err)
    except AttributeError as err:
        raise ExtensionError('Could not find %s' % objname +
                             (source and ' (needed for %s)' % source or ''),
                             err)


def encode_uri(uri):
    # type: (unicode) -> unicode
    split = list(urlsplit(uri))  # type: List[unicode]
    split[1] = split[1].encode('idna').decode('ascii')
    split[2] = quote_plus(split[2].encode('utf-8'), '/')
    query = list((q, v.encode('utf-8')) for (q, v) in parse_qsl(split[3]))
    split[3] = urlencode(query)
    return urlunsplit(split)


def display_chunk(chunk):
    # type: (Any) -> unicode
    if isinstance(chunk, (list, tuple)):
        if len(chunk) == 1:
            return text_type(chunk[0])
        return '%s .. %s' % (chunk[0], chunk[-1])
    return text_type(chunk)


def old_status_iterator(iterable, summary, color="darkgreen", stringify_func=display_chunk):
    # type: (Iterable, unicode, str, Callable[[Any], unicode]) -> Iterator
    l = 0
    for item in iterable:
        if l == 0:
            logger.info(bold(summary), nonl=True)
            l = 1
        logger.info(stringify_func(item), color=color, nonl=True)
        logger.info(" ", nonl=True)
        yield item
    if l == 1:
        logger.info('')


# new version with progress info
def status_iterator(iterable, summary, color="darkgreen", length=0, verbosity=0,
                    stringify_func=display_chunk):
    # type: (Iterable, unicode, str, int, int, Callable[[Any], unicode]) -> Iterable  # NOQA
    if length == 0:
        for item in old_status_iterator(iterable, summary, color, stringify_func):
            yield item
        return
    l = 0
    summary = bold(summary)
    for item in iterable:
        l += 1
        s = '%s[%3d%%] %s' % (summary, 100 * l / length, colorize(color, stringify_func(item)))
        if verbosity:
            s += '\n'
        else:
            s = term_width_line(s)
        logger.info(s, nonl=True)
        yield item
    if l > 0:
        logger.info('')


def epoch_to_rfc1123(epoch):
    # type: (float) -> unicode
    """Convert datetime format epoch to RFC1123."""
    from babel.dates import format_datetime

    dt = datetime.fromtimestamp(epoch)
    fmt = 'EEE, dd LLL yyyy hh:mm:ss'
    return format_datetime(dt, fmt, locale='en') + ' GMT'


def rfc1123_to_epoch(rfc1123):
    # type: (str) -> float
    return mktime(strptime(rfc1123, '%a, %d %b %Y %H:%M:%S %Z'))


def xmlname_checker():
    # type: () -> Pattern
    # https://www.w3.org/TR/REC-xml/#NT-Name
    # Only Python 3.3 or newer support character code in regular expression
    name_start_chars = [
        u':', [u'A', u'Z'], u'_',  [u'a', u'z'], [u'\u00C0', u'\u00D6'],
        [u'\u00D8', u'\u00F6'], [u'\u00F8', u'\u02FF'], [u'\u0370', u'\u037D'],
        [u'\u037F', u'\u1FFF'], [u'\u200C', u'\u200D'], [u'\u2070', u'\u218F'],
        [u'\u2C00', u'\u2FEF'], [u'\u3001', u'\uD7FF'], [u'\uF900', u'\uFDCF'],
        [u'\uFDF0', u'\uFFFD']]

    if sys.version_info.major == 3:
        name_start_chars.append([u'\U00010000', u'\U000EFFFF'])

    name_chars = [
        u"\\-", u"\\.", [u'0', u'9'], u'\u00B7', [u'\u0300', u'\u036F'],
        [u'\u203F', u'\u2040']
    ]

    def convert(entries, splitter=u'|'):
        # type: (Any, unicode) -> unicode
        results = []
        for entry in entries:
            if isinstance(entry, list):
                results.append(u'[%s]' % convert(entry, u'-'))
            else:
                results.append(entry)
        return splitter.join(results)

    start_chars_regex = convert(name_start_chars)
    name_chars_regex = convert(name_chars)
    return re.compile(u'(%s)(%s|%s)*' % (
        start_chars_regex, start_chars_regex, name_chars_regex))
