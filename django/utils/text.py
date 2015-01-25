import re
import unicodedata
import warnings
from gzip import GzipFile
from htmlentitydefs import name2codepoint

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.utils.encoding import force_unicode
from django.utils.functional import allow_lazy, SimpleLazyObject
from django.utils.translation import ugettext_lazy, ugettext as _, pgettext

# Capitalizes the first letter of a string.
capfirst = lambda x: x and force_unicode(x)[0].upper() + force_unicode(x)[1:]
capfirst = allow_lazy(capfirst, unicode)

# Set up regular expressions
re_words = re.compile(r'&.*?;|<.*?>|(\w[\w-]*)', re.U|re.S)
re_tag = re.compile(r'<(/)?([^ ]+?)(?: (/)| .*?)?>', re.S)


def wrap(text, width):
    """
    A word-wrap function that preserves existing line breaks and most spaces in
    the text. Expects that existing line breaks are posix newlines.
    """
    text = force_unicode(text)
    def _generator():
        it = iter(text.split(' '))
        word = it.next()
        yield word
        pos = len(word) - word.rfind('\n') - 1
        for word in it:
            if "\n" in word:
                lines = word.split('\n')
            else:
                lines = (word,)
            pos += len(lines[0]) + 1
            if pos > width:
                yield '\n'
                pos = len(lines[-1])
            else:
                yield ' '
                if len(lines) > 1:
                    pos = len(lines[-1])
            yield word
    return u''.join(_generator())
wrap = allow_lazy(wrap, unicode)


class Truncator(SimpleLazyObject):
    """
    An object used to truncate text, either by characters or words.
    """
    def __init__(self, text):
        super(Truncator, self).__init__(lambda: force_unicode(text))

    def add_truncation_text(self, text, truncate=None):
        if truncate is None:
            truncate = pgettext(
                'String to return when truncating text',
                u'%(truncated_text)s...')
        truncate = force_unicode(truncate)
        if '%(truncated_text)s' in truncate:
            return truncate % {'truncated_text': text}
        # The truncation text didn't contain the %(truncated_text)s string
        # replacement argument so just append it to the text.
        if text.endswith(truncate):
            # But don't append the truncation text if the current text already
            # ends in this.
            return text
        return '%s%s' % (text, truncate)

    def chars(self, num, truncate=None):
        """
        Returns the text truncated to be no longer than the specified number
        of characters.

        Takes an optional argument of what should be used to notify that the
        string has been truncated, defaulting to a translatable string of an
        ellipsis (...).
        """
        length = int(num)
        text = unicodedata.normalize('NFC', self._wrapped)

        # Calculate the length to truncate to (max length - end_text length)
        truncate_len = length
        for char in self.add_truncation_text('', truncate):
            if not unicodedata.combining(char):
                truncate_len -= 1
                if truncate_len == 0:
                    break

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
    chars = allow_lazy(chars)

    def words(self, num, truncate=None, html=False):
        """
        Truncates a string after a certain number of words. Takes an optional
        argument of what should be used to notify that the string has been
        truncated, defaulting to ellipsis (...).
        """
        length = int(num)
        if html:
            return self._html_words(length, truncate)
        return self._text_words(length, truncate)
    words = allow_lazy(words)

    def _text_words(self, length, truncate):
        """
        Truncates a string after a certain number of words.

        Newlines in the string will be stripped.
        """
        words = self._wrapped.split()
        if len(words) > length:
            words = words[:length]
            return self.add_truncation_text(u' '.join(words), truncate)
        return u' '.join(words)

    def _html_words(self, length, truncate):
        """
        Truncates HTML to a certain number of words (not counting tags and
        comments). Closes opened tags if they were correctly closed in the
        given HTML.

        Newlines in the HTML are preserved.
        """
        if length <= 0:
            return u''
        html4_singlets = (
            'br', 'col', 'link', 'base', 'img',
            'param', 'area', 'hr', 'input'
        )
        # Count non-HTML words and keep note of open tags
        pos = 0
        end_text_pos = 0
        words = 0
        open_tags = []
        while words <= length:
            m = re_words.search(self._wrapped, pos)
            if not m:
                # Checked through whole string
                break
            pos = m.end(0)
            if m.group(1):
                # It's an actual non-HTML word
                words += 1
                if words == length:
                    end_text_pos = pos
                continue
            # Check for tag
            tag = re_tag.match(m.group(0))
            if not tag or end_text_pos:
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
        if words <= length:
            # Don't try to close tags if we don't need to truncate
            return self._wrapped
        out = self._wrapped[:end_text_pos]
        truncate_text = self.add_truncation_text('', truncate)
        if truncate_text:
            out += truncate_text
        # Close any tags still open
        for tag in open_tags:
            out += '</%s>' % tag
        # Return string
        return out

def truncate_words(s, num, end_text='...'):
    warnings.warn('This function has been deprecated. Use the Truncator class '
        'in django.utils.text instead.', category=PendingDeprecationWarning)
    truncate = end_text and ' %s' % end_text or ''
    return Truncator(s).words(num, truncate=truncate)
truncate_words = allow_lazy(truncate_words, unicode)

def truncate_html_words(s, num, end_text='...'):
    warnings.warn('This function has been deprecated. Use the Truncator class '
        'in django.utils.text instead.', category=PendingDeprecationWarning)
    truncate = end_text and ' %s' % end_text or ''
    return Truncator(s).words(num, truncate=truncate, html=True)
truncate_html_words = allow_lazy(truncate_html_words, unicode)

def get_valid_filename(s):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Specifically, leading and trailing spaces are removed; other
    spaces are converted to underscores; and anything that is not a unicode
    alphanumeric, dash, underscore, or dot, is removed.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    u'johns_portrait_in_2004.jpg'
    """
    s = force_unicode(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)
get_valid_filename = allow_lazy(get_valid_filename, unicode)

def get_text_list(list_, last_word=ugettext_lazy(u'or')):
    """
    >>> get_text_list(['a', 'b', 'c', 'd'])
    u'a, b, c or d'
    >>> get_text_list(['a', 'b', 'c'], 'and')
    u'a, b and c'
    >>> get_text_list(['a', 'b'], 'and')
    u'a and b'
    >>> get_text_list(['a'])
    u'a'
    >>> get_text_list([])
    u''
    """
    if len(list_) == 0: return u''
    if len(list_) == 1: return force_unicode(list_[0])
    return u'%s %s %s' % (
        # Translators: This string is used as a separator between list elements
        _(', ').join([force_unicode(i) for i in list_][:-1]),
        force_unicode(last_word), force_unicode(list_[-1]))
get_text_list = allow_lazy(get_text_list, unicode)

def normalize_newlines(text):
    return force_unicode(re.sub(r'\r\n|\r|\n', '\n', text))
normalize_newlines = allow_lazy(normalize_newlines, unicode)

def recapitalize(text):
    "Recapitalizes text, placing caps after end-of-sentence punctuation."
    text = force_unicode(text).lower()
    capsRE = re.compile(r'(?:^|(?<=[\.\?\!] ))([a-z])')
    text = capsRE.sub(lambda x: x.group(1).upper(), text)
    return text
recapitalize = allow_lazy(recapitalize)

def phone2numeric(phone):
    "Converts a phone number with letters into its numeric equivalent."
    letters = re.compile(r'[A-Z]', re.I)
    char2number = lambda m: {'a': '2', 'b': '2', 'c': '2', 'd': '3', 'e': '3',
         'f': '3', 'g': '4', 'h': '4', 'i': '4', 'j': '5', 'k': '5', 'l': '5',
         'm': '6', 'n': '6', 'o': '6', 'p': '7', 'q': '7', 'r': '7', 's': '7',
         't': '8', 'u': '8', 'v': '8', 'w': '9', 'x': '9', 'y': '9', 'z': '9',
        }.get(m.group(0).lower())
    return letters.sub(char2number, phone)
phone2numeric = allow_lazy(phone2numeric)

# From http://www.xhaus.com/alan/python/httpcomp.html#gzip
# Used with permission.
def compress_string(s):
    zbuf = StringIO()
    zfile = GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
    zfile.write(s)
    zfile.close()
    return zbuf.getvalue()

ustring_re = re.compile(u"([\u0080-\uffff])")

# Backported from django 1.5
class StreamingBuffer(object):
    def __init__(self):
        self.vals = []

    def write(self, val):
        self.vals.append(val)

    def read(self):
        ret = ''.join(self.vals)
        self.vals = []
        return ret

    def flush(self):
        return

    def close(self):
        return

# Backported from django 1.5
# Like compress_string, but for iterators of strings.
def compress_sequence(sequence):
    buf = StreamingBuffer()
    zfile = GzipFile(mode='wb', compresslevel=6, fileobj=buf)
    # Output headers...
    yield buf.read()
    for item in sequence:
        zfile.write(item)
        zfile.flush()
        yield buf.read()
    zfile.close()
    yield buf.read()

def javascript_quote(s, quote_double_quotes=False):

    def fix(match):
        return r"\u%04x" % ord(match.group(1))

    if type(s) == str:
        s = s.decode('utf-8')
    elif type(s) != unicode:
        raise TypeError(s)
    s = s.replace('\\', '\\\\')
    s = s.replace('\r', '\\r')
    s = s.replace('\n', '\\n')
    s = s.replace('\t', '\\t')
    s = s.replace("'", "\\'")
    if quote_double_quotes:
        s = s.replace('"', '&quot;')
    return str(ustring_re.sub(fix, s))
javascript_quote = allow_lazy(javascript_quote, unicode)

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
    [u'This', u'is', u'"a person\\\'s"', u'test.']
    >>> list(smart_split(r"Another 'person\'s' test."))
    [u'Another', u"'person\\'s'", u'test.']
    >>> list(smart_split(r'A "\"funky\" style" test.'))
    [u'A', u'"\\"funky\\" style"', u'test.']
    """
    text = force_unicode(text)
    for bit in smart_split_re.finditer(text):
        yield bit.group(0)
smart_split = allow_lazy(smart_split, unicode)

def _replace_entity(match):
    text = match.group(1)
    if text[0] == u'#':
        text = text[1:]
        try:
            if text[0] in u'xX':
                c = int(text[1:], 16)
            else:
                c = int(text)
            return unichr(c)
        except ValueError:
            return match.group(0)
    else:
        try:
            return unichr(name2codepoint[text])
        except (ValueError, KeyError):
            return match.group(0)

_entity_re = re.compile(r"&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")

def unescape_entities(text):
    return _entity_re.sub(_replace_entity, text)
unescape_entities = allow_lazy(unescape_entities, unicode)

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
unescape_string_literal = allow_lazy(unescape_string_literal)
