"""HTML utilities suitable for global use."""

from __future__ import unicode_literals

import re
import sys
import warnings

from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_str, force_text
from django.utils.functional import allow_lazy
from django.utils.http import RFC3986_GENDELIMS, RFC3986_SUBDELIMS
from django.utils.safestring import SafeData, SafeText, mark_safe
from django.utils.six.moves.urllib.parse import (
    parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit,
)
from django.utils.text import normalize_newlines

from .html_parser import HTMLParseError, HTMLParser

# Configuration for urlize() function.
TRAILING_PUNCTUATION = ['.', ',', ':', ';', '.)', '"', '\'', '!']
WRAPPING_PUNCTUATION = [('(', ')'), ('<', '>'), ('[', ']'), ('&lt;', '&gt;'), ('"', '"'), ('\'', '\'')]

# List of possible strings used for bullets in bulleted lists.
DOTS = ['&middot;', '*', '\u2022', '&#149;', '&bull;', '&#8226;']

unencoded_ampersands_re = re.compile(r'&(?!(\w+|#\d+);)')
word_split_re = re.compile(r'(\s+)')
simple_url_re = re.compile(r'^https?://\[?\w', re.IGNORECASE)
simple_url_2_re = re.compile(r'^www\.|^(?!http)\w[^@]+\.(com|edu|gov|int|mil|net|org)($|/.*)$', re.IGNORECASE)
simple_email_re = re.compile(r'^\S+@\S+\.\S+$')
link_target_attribute_re = re.compile(r'(<a [^>]*?)target=[^\s>]+')
html_gunk_re = re.compile(
    r'(?:<br clear="all">|<i><\/i>|<b><\/b>|<em><\/em>|<strong><\/strong>|'
    '<\/?smallcaps>|<\/?uppercase>)', re.IGNORECASE)
hard_coded_bullets_re = re.compile(
    r'((?:<p>(?:%s).*?[a-zA-Z].*?</p>\s*)+)' % '|'.join(re.escape(x)
    for x in DOTS), re.DOTALL)
trailing_empty_content_re = re.compile(r'(?:<p>(?:&nbsp;|\s|<br \/>)*?</p>\s*)+\Z')


def escape(text):
    """
    Returns the given text with ampersands, quotes and angle brackets encoded
    for use in HTML.

    This function always escapes its input, even if it's already escaped and
    marked as such. This may result in double-escaping. If this is a concern,
    use conditional_escape() instead.
    """
    return mark_safe(force_text(text).replace('&', '&amp;').replace('<', '&lt;')
        .replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;'))
escape = allow_lazy(escape, six.text_type, SafeText)

_js_escapes = {
    ord('\\'): '\\u005C',
    ord('\''): '\\u0027',
    ord('"'): '\\u0022',
    ord('>'): '\\u003E',
    ord('<'): '\\u003C',
    ord('&'): '\\u0026',
    ord('='): '\\u003D',
    ord('-'): '\\u002D',
    ord(';'): '\\u003B',
    ord('\u2028'): '\\u2028',
    ord('\u2029'): '\\u2029'
}

# Escape every ASCII character with a value less than 32.
_js_escapes.update((ord('%c' % z), '\\u%04X' % z) for z in range(32))


def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    return mark_safe(force_text(value).translate(_js_escapes))
escapejs = allow_lazy(escapejs, six.text_type, SafeText)


def conditional_escape(text):
    """
    Similar to escape(), except that it doesn't operate on pre-escaped strings.

    This function relies on the __html__ convention used both by Django's
    SafeData class and by third-party libraries like markupsafe.
    """
    if hasattr(text, '__html__'):
        return text.__html__()
    else:
        return escape(text)


def format_html(format_string, *args, **kwargs):
    """
    Similar to str.format, but passes all arguments through conditional_escape,
    and calls 'mark_safe' on the result. This function should be used instead
    of str.format or % interpolation to build up small HTML fragments.
    """
    args_safe = map(conditional_escape, args)
    kwargs_safe = {k: conditional_escape(v) for (k, v) in six.iteritems(kwargs)}
    return mark_safe(format_string.format(*args_safe, **kwargs_safe))


def format_html_join(sep, format_string, args_generator):
    """
    A wrapper of format_html, for the common case of a group of arguments that
    need to be formatted using the same format string, and then joined using
    'sep'. 'sep' is also passed through conditional_escape.

    'args_generator' should be an iterator that returns the sequence of 'args'
    that will be passed to format_html.

    Example:

      format_html_join('\n', "<li>{} {}</li>", ((u.first_name, u.last_name)
                                                  for u in users))

    """
    return mark_safe(conditional_escape(sep).join(
        format_html(format_string, *tuple(args))
        for args in args_generator))


def linebreaks(value, autoescape=False):
    """Converts newlines into <p> and <br />s."""
    value = normalize_newlines(value)
    paras = re.split('\n{2,}', value)
    if autoescape:
        paras = ['<p>%s</p>' % escape(p).replace('\n', '<br />') for p in paras]
    else:
        paras = ['<p>%s</p>' % p.replace('\n', '<br />') for p in paras]
    return '\n\n'.join(paras)
linebreaks = allow_lazy(linebreaks, six.text_type)


class MLStripper(HTMLParser):
    def __init__(self):
        # The strict parameter was added in Python 3.2 with a default of True.
        # The default changed to False in Python 3.3 and was deprecated.
        if sys.version_info[:2] == (3, 2):
            HTMLParser.__init__(self, strict=False)
        else:
            HTMLParser.__init__(self)
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def handle_entityref(self, name):
        self.fed.append('&%s;' % name)

    def handle_charref(self, name):
        self.fed.append('&#%s;' % name)

    def get_data(self):
        return ''.join(self.fed)


def _strip_once(value):
    """
    Internal tag stripping utility used by strip_tags.
    """
    s = MLStripper()
    try:
        s.feed(value)
    except HTMLParseError:
        return value
    try:
        s.close()
    except (HTMLParseError, UnboundLocalError):
        # UnboundLocalError because of http://bugs.python.org/issue17802
        # on Python 3.2, triggered by strict=False mode of HTMLParser
        return s.get_data() + s.rawdata
    else:
        return s.get_data()


def strip_tags(value):
    """Returns the given HTML with all tags stripped."""
    # Note: in typical case this loop executes _strip_once once. Loop condition
    # is redundant, but helps to reduce number of executions of _strip_once.
    while '<' in value and '>' in value:
        new_value = _strip_once(value)
        if len(new_value) >= len(value):
            # _strip_once was not able to detect more tags or length increased
            # due to http://bugs.python.org/issue20288
            # (affects Python 2 < 2.7.7 and Python 3 < 3.3.5)
            break
        value = new_value
    return value
strip_tags = allow_lazy(strip_tags)


def remove_tags(html, tags):
    """Returns the given HTML with given tags removed."""
    warnings.warn(
        "django.utils.html.remove_tags() and the removetags template filter "
        "are deprecated. Consider using the bleach library instead.",
        RemovedInDjango20Warning, stacklevel=3
    )
    tags = [re.escape(tag) for tag in tags.split()]
    tags_re = '(%s)' % '|'.join(tags)
    starttag_re = re.compile(r'<%s(/?>|(\s+[^>]*>))' % tags_re, re.U)
    endtag_re = re.compile('</%s>' % tags_re)
    html = starttag_re.sub('', html)
    html = endtag_re.sub('', html)
    return html
remove_tags = allow_lazy(remove_tags, six.text_type)


def strip_spaces_between_tags(value):
    """Returns the given HTML with spaces between tags removed."""
    return re.sub(r'>\s+<', '><', force_text(value))
strip_spaces_between_tags = allow_lazy(strip_spaces_between_tags, six.text_type)


def strip_entities(value):
    """Returns the given HTML with all entities (&something;) stripped."""
    warnings.warn(
        "django.utils.html.strip_entities() is deprecated.",
        RemovedInDjango20Warning, stacklevel=2
    )
    return re.sub(r'&(?:\w+|#\d+);', '', force_text(value))
strip_entities = allow_lazy(strip_entities, six.text_type)


def smart_urlquote(url):
    "Quotes a URL if it isn't already quoted."
    def unquote_quote(segment):
        segment = unquote(force_str(segment))
        # Tilde is part of RFC3986 Unreserved Characters
        # http://tools.ietf.org/html/rfc3986#section-2.3
        # See also http://bugs.python.org/issue16285
        segment = quote(segment, safe=RFC3986_SUBDELIMS + RFC3986_GENDELIMS + str('~'))
        return force_text(segment)

    # Handle IDN before quoting.
    try:
        scheme, netloc, path, query, fragment = urlsplit(url)
    except ValueError:
        # invalid IPv6 URL (normally square brackets in hostname part).
        return unquote_quote(url)

    try:
        netloc = netloc.encode('idna').decode('ascii')  # IDN -> ACE
    except UnicodeError:  # invalid domain part
        return unquote_quote(url)

    if query:
        # Separately unquoting key/value, so as to not mix querystring separators
        # included in query values. See #22267.
        query_parts = [(unquote(force_str(q[0])), unquote(force_str(q[1])))
                       for q in parse_qsl(query, keep_blank_values=True)]
        # urlencode will take care of quoting
        query = urlencode(query_parts)

    path = unquote_quote(path)
    fragment = unquote_quote(fragment)

    return urlunsplit((scheme, netloc, path, query, fragment))


def urlize(text, trim_url_limit=None, nofollow=False, autoescape=False):
    """
    Converts any URLs in text into clickable links.

    Works on http://, https://, www. links, and also on links ending in one of
    the original seven gTLDs (.com, .edu, .gov, .int, .mil, .net, and .org).
    Links can have trailing punctuation (periods, commas, close-parens) and
    leading punctuation (opening parens) and it'll still do the right thing.

    If trim_url_limit is not None, the URLs in the link text longer than this
    limit will be truncated to trim_url_limit-3 characters and appended with
    an ellipsis.

    If nofollow is True, the links will get a rel="nofollow" attribute.

    If autoescape is True, the link text and URLs will be autoescaped.
    """
    safe_input = isinstance(text, SafeData)

    def trim_url(x, limit=trim_url_limit):
        if limit is None or len(x) <= limit:
            return x
        return '%s...' % x[:max(0, limit - 3)]

    def unescape(text, trail):
        """
        If input URL is HTML-escaped, unescape it so as we can safely feed it to
        smart_urlquote. For example:
        http://example.com?x=1&amp;y=&lt;2&gt; => http://example.com?x=1&y=<2>
        """
        unescaped = (text + trail).replace(
            '&amp;', '&').replace('&lt;', '<').replace(
            '&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
        if trail and unescaped.endswith(trail):
            # Remove trail for unescaped if it was not consumed by unescape
            unescaped = unescaped[:-len(trail)]
        elif trail == ';':
            # Trail was consumed by unescape (as end-of-entity marker), move it to text
            text += trail
            trail = ''
        return text, unescaped, trail

    words = word_split_re.split(force_text(text))
    for i, word in enumerate(words):
        if '.' in word or '@' in word or ':' in word:
            # Deal with punctuation.
            lead, middle, trail = '', word, ''
            for punctuation in TRAILING_PUNCTUATION:
                if middle.endswith(punctuation):
                    middle = middle[:-len(punctuation)]
                    trail = punctuation + trail
            for opening, closing in WRAPPING_PUNCTUATION:
                if middle.startswith(opening):
                    middle = middle[len(opening):]
                    lead = lead + opening
                # Keep parentheses at the end only if they're balanced.
                if (middle.endswith(closing)
                        and middle.count(closing) == middle.count(opening) + 1):
                    middle = middle[:-len(closing)]
                    trail = closing + trail

            # Make URL we want to point to.
            url = None
            nofollow_attr = ' rel="nofollow"' if nofollow else ''
            if simple_url_re.match(middle):
                middle, middle_unescaped, trail = unescape(middle, trail)
                url = smart_urlquote(middle_unescaped)
            elif simple_url_2_re.match(middle):
                middle, middle_unescaped, trail = unescape(middle, trail)
                url = smart_urlquote('http://%s' % middle_unescaped)
            elif ':' not in middle and simple_email_re.match(middle):
                local, domain = middle.rsplit('@', 1)
                try:
                    domain = domain.encode('idna').decode('ascii')
                except UnicodeError:
                    continue
                url = 'mailto:%s@%s' % (local, domain)
                nofollow_attr = ''

            # Make link.
            if url:
                trimmed = trim_url(middle)
                if autoescape and not safe_input:
                    lead, trail = escape(lead), escape(trail)
                    trimmed = escape(trimmed)
                middle = '<a href="%s"%s>%s</a>' % (escape(url), nofollow_attr, trimmed)
                words[i] = mark_safe('%s%s%s' % (lead, middle, trail))
            else:
                if safe_input:
                    words[i] = mark_safe(word)
                elif autoescape:
                    words[i] = escape(word)
        elif safe_input:
            words[i] = mark_safe(word)
        elif autoescape:
            words[i] = escape(word)
    return ''.join(words)
urlize = allow_lazy(urlize, six.text_type)


def avoid_wrapping(value):
    """
    Avoid text wrapping in the middle of a phrase by adding non-breaking
    spaces where there previously were normal spaces.
    """
    return value.replace(" ", "\xa0")


def html_safe(klass):
    """
    A decorator that defines the __html__ method. This helps non-Django
    templates to detect classes whose __str__ methods return SafeText.
    """
    if '__html__' in klass.__dict__:
        raise ValueError(
            "can't apply @html_safe to %s because it defines "
            "__html__()." % klass.__name__
        )
    if six.PY2:
        if '__unicode__' not in klass.__dict__:
            raise ValueError(
                "can't apply @html_safe to %s because it doesn't "
                "define __unicode__()." % klass.__name__
            )
        klass_unicode = klass.__unicode__
        klass.__unicode__ = lambda self: mark_safe(klass_unicode(self))
        klass.__html__ = lambda self: unicode(self)
    else:
        if '__str__' not in klass.__dict__:
            raise ValueError(
                "can't apply @html_safe to %s because it doesn't "
                "define __str__()." % klass.__name__
            )
        klass_str = klass.__str__
        klass.__str__ = lambda self: mark_safe(klass_str(self))
        klass.__html__ = lambda self: str(self)
    return klass
