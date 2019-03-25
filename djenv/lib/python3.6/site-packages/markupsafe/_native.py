# -*- coding: utf-8 -*-
"""
markupsafe._native
~~~~~~~~~~~~~~~~~~

Native Python implementation used when the C module is not compiled.

:copyright: © 2010 by the Pallets team.
:license: BSD, see LICENSE for more details.
"""
from . import Markup
from ._compat import text_type


def escape(s):
    """Replace the characters ``&``, ``<``, ``>``, ``'``, and ``"`` in
    the string with HTML-safe sequences. Use this if you need to display
    text that might contain such characters in HTML.

    If the object has an ``__html__`` method, it is called and the
    return value is assumed to already be safe for HTML.

    :param s: An object to be converted to a string and escaped.
    :return: A :class:`Markup` string with the escaped text.
    """
    if hasattr(s, "__html__"):
        return Markup(s.__html__())
    return Markup(
        text_type(s)
        .replace("&", "&amp;")
        .replace(">", "&gt;")
        .replace("<", "&lt;")
        .replace("'", "&#39;")
        .replace('"', "&#34;")
    )


def escape_silent(s):
    """Like :func:`escape` but treats ``None`` as the empty string.
    Useful with optional values, as otherwise you get the string
    ``'None'`` when the value is ``None``.

    >>> escape(None)
    Markup('None')
    >>> escape_silent(None)
    Markup('')
    """
    if s is None:
        return Markup()
    return escape(s)


def soft_unicode(s):
    """Convert an object to a string if it isn't already. This preserves
    a :class:`Markup` string rather than converting it back to a basic
    string, so it will still be marked as safe and won't be escaped
    again.

    >>> value = escape('<User 1>')
    >>> value
    Markup('&lt;User 1&gt;')
    >>> escape(str(value))
    Markup('&amp;lt;User 1&amp;gt;')
    >>> escape(soft_unicode(value))
    Markup('&lt;User 1&gt;')
    """
    if not isinstance(s, text_type):
        s = text_type(s)
    return s
