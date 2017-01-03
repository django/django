from __future__ import unicode_literals

import re
import unicodedata
from gzip import GzipFile
from io import BytesIO

from django.utils import six
from django.utils.encoding import force_text
from django.utils.functional import (
    SimpleLazyObject, keep_lazy, keep_lazy_text, lazy,
)
from django.utils.safestring import SafeText, mark_safe
from django.utils.six.moves import html_entities
from django.utils.translation import pgettext, ugettext as _, ugettext_lazy

if six.PY2:
    # Import force_unicode even though this module doesn't use it, because some
    # people rely on it being here.
    from django.utils.encoding import force_unicode  # NOQA


@keep_lazy_text
def capfirst(x):
    """Capitalize the first letter of a string."""
    return x and force_text(x)[0].upper() + force_text(x)[1:]


# Set up regular expressions
re_words = re.compile(r'<.*?>|((?:\w[-\w]*|&.*?;)+)', re.U | re.S)
re_chars = re.compile(r'<.*?>|(.)', re.U | re.S)
re_tag = re.compile(r'<(/)?([^ ]+?)(?:(\s*/)| .*?)?>', re.S)
re_newlines = re.compile(r'\r\n|\r')  # Used in normalize_newlines
re_camel_case = re.compile(r'(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))')


@keep_lazy_text
def wrap(text, width):
    """
    A word-wrap function that preserves existing line breaks. Expects that
    existing line breaks are posix newlines.

    All white space is preserved except added line breaks consume the space on
    which they break the line.

    Long words are not wrapped, so the output text may have lines longer than
    ``width``.
    """
    text = force_text(text)

    def _generator():
        for line in text.splitlines(True):  # True keeps trailing linebreaks
            max_width = min((line.endswith('\n') and width + 1 or width), width)
            while len(line) > max_width:
                space = line[:max_width + 1].rfind(' ') + 1
                if space == 0:
                    space = line.find(' ') + 1
                    if space == 0:
                        yield line
                        line = ''
                        break
                yield '%s\n' % line[:space - 1]
                line = line[space:]
                max_width = min((line.endswith('\n') and width + 1 or width), width)
            if line:
                yield line
    return ''.join(_generator())


class Truncator(SimpleLazyObject):
    """
    An object used to truncate text, either by characters or words.
    """
    def __init__(self, text):
        super(Truncator, self).__init__(lambda: force_text(text))

    def add_truncation_text(self, text, truncate=None):
        if truncate is None:
            truncate = pgettext(
                'String to return when truncating text',
                '%(truncated_text)s...')
        truncate = force_text(truncate)
        if '%(truncated_text)s' in truncate:
            return truncate % {'truncated_text': text}
        # The truncation text didn't contain the %(truncated_text)s string
        # replacement argument so just append it to the text.
        if text.endswith(truncate):
            # But don't append the truncation text if the current text already
            # ends in this.
            return text
        return '%s%s' % (text, truncate)

    def chars(self, num, truncate=None, html=False):
        """
        Returns the text truncated to be no longer than the specified number
        of characters.

        Takes an optional argument of what should be used to notify that the
        string has been truncated, defaulting to a translatable string of an
        ellipsis (...).
        """
        self._setup()
        length = int(num)
        text = unicodedata.normalize('NFC', self._wrapped)

        # Calculate the length to truncate to (max length - end_text length)
        truncate_len = length
        for char in self.add_truncation_text('', truncate):
            if not unicodedata.combining(char):
                truncate_len -= 1
                if truncate_len == 0:
                    break
        if html:
            return self._truncate_html(length, truncate, text, truncate_len, False)
        return self._text_chars(length, truncate, text, truncate_len)

    def _text_chars(self, length, truncate, text, truncate_len):
        """
        Truncates a string after a certain number of chars.
        """
        s_len = 0
        end_index = None
        for i, char in enumerate(text):
            if unicodedata.combining(char):
                # Don't consider combining characters
                # as adding to the string length
                continue
            s_len += 1
            if end_index is None and s_len > truncate_len:
                end_index = i
            if s_len > length:
                # Return the truncated string
                return self.add_truncation_text(text[:end_index or 0],
                                                truncate)

        # Return the original string since no truncation was necessary
        return text

    def words(self, num, truncate=None, html=False):
        """
        Truncates a string after a certain number of words. Takes an optional
        argument of what should be used to notify that the string has been
        truncated, defaulting to ellipsis (...).
        """
        self._setup()
        length = int(num)
        if html:
            return self._truncate_html(length, truncate, self._wrapped, length, True)
        return self._text_words(length, truncate)

    def _text_words(self, length, truncate):
        """
        Truncates a string after a certain number of words.

        Newlines in the string will be stripped.
        """
        words = self._wrapped.split()
        if len(words) > length:
            words = words[:length]
            return self.add_truncation_text(' '.join(words), truncate)
        return ' '.join(words)

    def _truncate_html(self, length, truncate, text, truncate_len, words):
        """
        Truncates HTML to a certain number of chars (not counting tags and
        comments), or, if words is True, then to a certain number of words.
        Closes opened tags if they were correctly closed in the given HTML.

        Newlines in the HTML are preserved.
        """
        if words and length <= 0:
            return ''

        html4_singlets = (
            'br', 'col', 'link', 'base', 'img',
            'param', 'area', 'hr', 'input'
        )

        # Count non-HTML chars/words and keep note of open tags
        pos = 0
        end_text_pos = 0
        current_len = 0
        open_tags = []

        regex = re_words if words else re_chars

        while current_len <= length:
            m = regex.search(text, pos)
            if not m:
                # Checked through whole string
                break
            pos = m.end(0)
            if m.group(1):
                # It's an actual non-HTML word or char
                current_len += 1
                if current_len == truncate_len:
                    end_text_pos = pos
                continue
            # Check for tag
            tag = re_tag.match(m.group(0))
            if not tag or current_len >= truncate_len:
                # Don't worry about non tags or tags after our truncate point
                continue
            closing_tag, tagname, self_closing = tag.groups()
            # Element names are always case-insensitive
            tagname = tagname.lower()
            if self_closing or tagname in html4_singlets:
                pass
            elif closing_tag:
                # Check for match in open tags list
                try:
                    i = open_tags.index(tagname)
                except ValueError:
                    pass
                else:
                    # SGML: An end tag closes, back to the matching start tag,
                    # all unclosed intervening start tags with omitted end tags
                    open_tags = open_tags[i + 1:]
            else:
                # Add it to the start of the open tags list
                open_tags.insert(0, tagname)

        if current_len <= length:
            return text
        out = text[:end_text_pos]
        truncate_text = self.add_truncation_text('', truncate)
        if truncate_text:
            out += truncate_text
        # Close any tags still open
        for tag in open_tags:
            out += '</%s>' % tag
        # Return string
        return out


@keep_lazy_text
def get_valid_filename(s):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Specifically, leading and trailing spaces are removed; other
    spaces are converted to underscores; and anything that is not a unicode
    alphanumeric, dash, underscore, or dot, is removed.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'
    """
    s = force_text(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


@keep_lazy_text
def get_text_list(list_, last_word=ugettext_lazy('or')):
    """
    >>> get_text_list(['a', 'b', 'c', 'd'])
    'a, b, c or d'
    >>> get_text_list(['a', 'b', 'c'], 'and')
    'a, b and c'
    >>> get_text_list(['a', 'b'], 'and')
    'a and b'
    >>> get_text_list(['a'])
    'a'
    >>> get_text_list([])
    ''
    """
    if len(list_) == 0:
        return ''
    if len(list_) == 1:
        return force_text(list_[0])
    return '%s %s %s' % (
        # Translators: This string is used as a separator between list elements
        _(', ').join(force_text(i) for i in list_[:-1]),
        force_text(last_word), force_text(list_[-1]))


@keep_lazy_text
def normalize_newlines(text):
    """Normalizes CRLF and CR newlines to just LF."""
    text = force_text(text)
    return re_newlines.sub('\n', text)


@keep_lazy_text
def phone2numeric(phone):
    """Converts a phone number with letters into its numeric equivalent."""
    char2number = {
        'a': '2', 'b': '2', 'c': '2', 'd': '3', 'e': '3', 'f': '3', 'g': '4',
        'h': '4', 'i': '4', 'j': '5', 'k': '5', 'l': '5', 'm': '6', 'n': '6',
        'o': '6', 'p': '7', 'q': '7', 'r': '7', 's': '7', 't': '8', 'u': '8',
        'v': '8', 'w': '9', 'x': '9', 'y': '9', 'z': '9',
    }
    return ''.join(char2number.get(c, c) for c in phone.lower())


# From http://www.xhaus.com/alan/python/httpcomp.html#gzip
# Used with permission.
def compress_string(s):
    zbuf = BytesIO()
    with GzipFile(mode='wb', compresslevel=6, fileobj=zbuf, mtime=0) as zfile:
        zfile.write(s)
    return zbuf.getvalue()


class StreamingBuffer(object):
    def __init__(self):
        self.vals = []

    def write(self, val):
        self.vals.append(val)

    def read(self):
        if not self.vals:
            return b''
        ret = b''.join(self.vals)
        self.vals = []
        return ret

    def flush(self):
        return

    def close(self):
        return


# Like compress_string, but for iterators of strings.
def compress_sequence(sequence):
    buf = StreamingBuffer()
    with GzipFile(mode='wb', compresslevel=6, fileobj=buf, mtime=0) as zfile:
        # Output headers...
        yield buf.read()
        for item in sequence:
            zfile.write(item)
            data = buf.read()
            if data:
                yield data
    yield buf.read()


# Expression to match some_token and some_token="with spaces" (and similarly
# for single-quoted strings).
smart_split_re = re.compile(r"""
    ((?:
        [^\s'"]*
        (?:
            (?:"(?:[^"\\]|\\.)*" | '(?:[^'\\]|\\.)*')
            [^\s'"]*
        )+
    ) | \S+)
""", re.VERBOSE)


def smart_split(text):
    r"""
    Generator that splits a string by spaces, leaving quoted phrases together.
    Supports both single and double quotes, and supports escaping quotes with
    backslashes. In the output, strings will keep their initial and trailing
    quote marks and escaped quotes will remain escaped (the results can then
    be further processed with unescape_string_literal()).

    >>> list(smart_split(r'This is "a person\'s" test.'))
    ['This', 'is', '"a person\\\'s"', 'test.']
    >>> list(smart_split(r"Another 'person\'s' test."))
    ['Another', "'person\\'s'", 'test.']
    >>> list(smart_split(r'A "\"funky\" style" test.'))
    ['A', '"\\"funky\\" style"', 'test.']
    """
    text = force_text(text)
    for bit in smart_split_re.finditer(text):
        yield bit.group(0)


def _replace_entity(match):
    text = match.group(1)
    if text[0] == '#':
        text = text[1:]
        try:
            if text[0] in 'xX':
                c = int(text[1:], 16)
            else:
                c = int(text)
            return six.unichr(c)
        except ValueError:
            return match.group(0)
    else:
        try:
            return six.unichr(html_entities.name2codepoint[text])
        except (ValueError, KeyError):
            return match.group(0)


_entity_re = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")


@keep_lazy_text
def unescape_entities(text):
    return _entity_re.sub(_replace_entity, force_text(text))


@keep_lazy_text
def unescape_string_literal(s):
    r"""
    Convert quoted string literals to unquoted strings with escaped quotes and
    backslashes unquoted::

        >>> unescape_string_literal('"abc"')
        'abc'
        >>> unescape_string_literal("'abc'")
        'abc'
        >>> unescape_string_literal('"a \"bc\""')
        'a "bc"'
        >>> unescape_string_literal("'\'ab\' c'")
        "'ab' c"
    """
    if s[0] not in "\"'" or s[-1] != s[0]:
        raise ValueError("Not a string literal: %r" % s)
    quote = s[0]
    return s[1:-1].replace(r'\%s' % quote, quote).replace(r'\\', '\\')


@keep_lazy(six.text_type, SafeText)
def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = force_text(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
        value = re.sub(r'[^\w\s-]', '', value, flags=re.U).strip().lower()
        return mark_safe(re.sub(r'[-\s]+', '-', value, flags=re.U))
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return mark_safe(re.sub(r'[-\s]+', '-', value))


def camel_case_to_spaces(value):
    """
    Splits CamelCase and converts to lower case. Also strips leading and
    trailing whitespace.
    """
    return re_camel_case.sub(r' \1', value).strip().lower()


def _format_lazy(format_string, *args, **kwargs):
    """
    Apply str.format() on 'format_string' where format_string, args,
    and/or kwargs might be lazy.
    """
    return format_string.format(*args, **kwargs)


format_lazy = lazy(_format_lazy, six.text_type)
