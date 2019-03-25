# -*- coding: utf-8 -*-
"""
markupsafe
~~~~~~~~~~

Implements an escape function and a Markup string to replace HTML
special characters with safe representations.

:copyright: © 2010 by the Pallets team.
:license: BSD, see LICENSE for more details.
"""
import re
import string

from ._compat import int_types
from ._compat import iteritems
from ._compat import Mapping
from ._compat import PY2
from ._compat import string_types
from ._compat import text_type
from ._compat import unichr

__version__ = "1.1.0"

__all__ = ["Markup", "soft_unicode", "escape", "escape_silent"]

_striptags_re = re.compile(r"(<!--.*?-->|<[^>]*>)")
_entity_re = re.compile(r"&([^& ;]+);")


class Markup(text_type):
    """A string that is ready to be safely inserted into an HTML or XML
    document, either because it was escaped or because it was marked
    safe.

    Passing an object to the constructor converts it to text and wraps
    it to mark it safe without escaping. To escape the text, use the
    :meth:`escape` class method instead.

    >>> Markup('Hello, <em>World</em>!')
    Markup('Hello, <em>World</em>!')
    >>> Markup(42)
    Markup('42')
    >>> Markup.escape('Hello, <em>World</em>!')
    Markup('Hello &lt;em&gt;World&lt;/em&gt;!')

    This implements the ``__html__()`` interface that some frameworks
    use. Passing an object that implements ``__html__()`` will wrap the
    output of that method, marking it safe.

    >>> class Foo:
    ...     def __html__(self):
    ...         return '<a href="/foo">foo</a>'
    ...
    >>> Markup(Foo())
    Markup('<a href="/foo">foo</a>')

    This is a subclass of the text type (``str`` in Python 3,
    ``unicode`` in Python 2). It has the same methods as that type, but
    all methods escape their arguments and return a ``Markup`` instance.

    >>> Markup('<em>%s</em>') % 'foo & bar'
    Markup('<em>foo &amp; bar</em>')
    >>> Markup('<em>Hello</em> ') + '<foo>'
    Markup('<em>Hello</em> &lt;foo&gt;')
    """

    __slots__ = ()

    def __new__(cls, base=u"", encoding=None, errors="strict"):
        if hasattr(base, "__html__"):
            base = base.__html__()
        if encoding is None:
            return text_type.__new__(cls, base)
        return text_type.__new__(cls, base, encoding, errors)

    def __html__(self):
        return self

    def __add__(self, other):
        if isinstance(other, string_types) or hasattr(other, "__html__"):
            return self.__class__(super(Markup, self).__add__(self.escape(other)))
        return NotImplemented

    def __radd__(self, other):
        if hasattr(other, "__html__") or isinstance(other, string_types):
            return self.escape(other).__add__(self)
        return NotImplemented

    def __mul__(self, num):
        if isinstance(num, int_types):
            return self.__class__(text_type.__mul__(self, num))
        return NotImplemented

    __rmul__ = __mul__

    def __mod__(self, arg):
        if isinstance(arg, tuple):
            arg = tuple(_MarkupEscapeHelper(x, self.escape) for x in arg)
        else:
            arg = _MarkupEscapeHelper(arg, self.escape)
        return self.__class__(text_type.__mod__(self, arg))

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, text_type.__repr__(self))

    def join(self, seq):
        return self.__class__(text_type.join(self, map(self.escape, seq)))

    join.__doc__ = text_type.join.__doc__

    def split(self, *args, **kwargs):
        return list(map(self.__class__, text_type.split(self, *args, **kwargs)))

    split.__doc__ = text_type.split.__doc__

    def rsplit(self, *args, **kwargs):
        return list(map(self.__class__, text_type.rsplit(self, *args, **kwargs)))

    rsplit.__doc__ = text_type.rsplit.__doc__

    def splitlines(self, *args, **kwargs):
        return list(map(self.__class__, text_type.splitlines(self, *args, **kwargs)))

    splitlines.__doc__ = text_type.splitlines.__doc__

    def unescape(self):
        """Convert escaped markup back into a text string. This replaces
        HTML entities with the characters they represent.

        >>> Markup('Main &raquo; <em>About</em>').unescape()
        'Main » <em>About</em>'
        """
        from ._constants import HTML_ENTITIES

        def handle_match(m):
            name = m.group(1)
            if name in HTML_ENTITIES:
                return unichr(HTML_ENTITIES[name])
            try:
                if name[:2] in ("#x", "#X"):
                    return unichr(int(name[2:], 16))
                elif name.startswith("#"):
                    return unichr(int(name[1:]))
            except ValueError:
                pass
            # Don't modify unexpected input.
            return m.group()

        return _entity_re.sub(handle_match, text_type(self))

    def striptags(self):
        """:meth:`unescape` the markup, remove tags, and normalize
        whitespace to single spaces.

        >>> Markup('Main &raquo;\t<em>About</em>').striptags()
        'Main » About'
        """
        stripped = u" ".join(_striptags_re.sub("", self).split())
        return Markup(stripped).unescape()

    @classmethod
    def escape(cls, s):
        """Escape a string. Calls :func:`escape` and ensures that for
        subclasses the correct type is returned.
        """
        rv = escape(s)
        if rv.__class__ is not cls:
            return cls(rv)
        return rv

    def make_simple_escaping_wrapper(name):  # noqa: B902
        orig = getattr(text_type, name)

        def func(self, *args, **kwargs):
            args = _escape_argspec(list(args), enumerate(args), self.escape)
            _escape_argspec(kwargs, iteritems(kwargs), self.escape)
            return self.__class__(orig(self, *args, **kwargs))

        func.__name__ = orig.__name__
        func.__doc__ = orig.__doc__
        return func

    for method in (
        "__getitem__",
        "capitalize",
        "title",
        "lower",
        "upper",
        "replace",
        "ljust",
        "rjust",
        "lstrip",
        "rstrip",
        "center",
        "strip",
        "translate",
        "expandtabs",
        "swapcase",
        "zfill",
    ):
        locals()[method] = make_simple_escaping_wrapper(method)

    def partition(self, sep):
        return tuple(map(self.__class__, text_type.partition(self, self.escape(sep))))

    def rpartition(self, sep):
        return tuple(map(self.__class__, text_type.rpartition(self, self.escape(sep))))

    def format(self, *args, **kwargs):
        formatter = EscapeFormatter(self.escape)
        kwargs = _MagicFormatMapping(args, kwargs)
        return self.__class__(formatter.vformat(self, args, kwargs))

    def __html_format__(self, format_spec):
        if format_spec:
            raise ValueError("Unsupported format specification " "for Markup.")
        return self

    # not in python 3
    if hasattr(text_type, "__getslice__"):
        __getslice__ = make_simple_escaping_wrapper("__getslice__")

    del method, make_simple_escaping_wrapper


class _MagicFormatMapping(Mapping):
    """This class implements a dummy wrapper to fix a bug in the Python
    standard library for string formatting.

    See http://bugs.python.org/issue13598 for information about why
    this is necessary.
    """

    def __init__(self, args, kwargs):
        self._args = args
        self._kwargs = kwargs
        self._last_index = 0

    def __getitem__(self, key):
        if key == "":
            idx = self._last_index
            self._last_index += 1
            try:
                return self._args[idx]
            except LookupError:
                pass
            key = str(idx)
        return self._kwargs[key]

    def __iter__(self):
        return iter(self._kwargs)

    def __len__(self):
        return len(self._kwargs)


if hasattr(text_type, "format"):

    class EscapeFormatter(string.Formatter):
        def __init__(self, escape):
            self.escape = escape

        def format_field(self, value, format_spec):
            if hasattr(value, "__html_format__"):
                rv = value.__html_format__(format_spec)
            elif hasattr(value, "__html__"):
                if format_spec:
                    raise ValueError(
                        "Format specifier {0} given, but {1} does not"
                        " define __html_format__. A class that defines"
                        " __html__ must define __html_format__ to work"
                        " with format specifiers.".format(format_spec, type(value))
                    )
                rv = value.__html__()
            else:
                # We need to make sure the format spec is unicode here as
                # otherwise the wrong callback methods are invoked.  For
                # instance a byte string there would invoke __str__ and
                # not __unicode__.
                rv = string.Formatter.format_field(self, value, text_type(format_spec))
            return text_type(self.escape(rv))


def _escape_argspec(obj, iterable, escape):
    """Helper for various string-wrapped functions."""
    for key, value in iterable:
        if hasattr(value, "__html__") or isinstance(value, string_types):
            obj[key] = escape(value)
    return obj


class _MarkupEscapeHelper(object):
    """Helper for Markup.__mod__"""

    def __init__(self, obj, escape):
        self.obj = obj
        self.escape = escape

    def __getitem__(self, item):
        return _MarkupEscapeHelper(self.obj[item], self.escape)

    def __str__(self):
        return text_type(self.escape(self.obj))

    __unicode__ = __str__

    def __repr__(self):
        return str(self.escape(repr(self.obj)))

    def __int__(self):
        return int(self.obj)

    def __float__(self):
        return float(self.obj)


# we have to import it down here as the speedups and native
# modules imports the markup type which is define above.
try:
    from ._speedups import escape, escape_silent, soft_unicode
except ImportError:
    from ._native import escape, escape_silent, soft_unicode

if not PY2:
    soft_str = soft_unicode
    __all__.append("soft_str")
