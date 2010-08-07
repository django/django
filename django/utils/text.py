import re
from django.utils.encoding import force_unicode
from django.utils.functional import allow_lazy
from django.utils.translation import ugettext_lazy
from htmlentitydefs import name2codepoint

# Capitalizes the first letter of a string.
capfirst = lambda x: x and force_unicode(x)[0].upper() + force_unicode(x)[1:]
capfirst = allow_lazy(capfirst, unicode)

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

def truncate_words(s, num, end_text='...'):
    """Truncates a string after a certain number of words. Takes an optional
    argument of what should be used to notify that the string has been
    truncated, defaulting to ellipsis (...)

    Newlines in the string will be stripped.
    """
    s = force_unicode(s)
    length = int(num)
    words = s.split()
    if len(words) > length:
        words = words[:length]
        if not words[-1].endswith(end_text):
            words.append(end_text)
    return u' '.join(words)
truncate_words = allow_lazy(truncate_words, unicode)

def truncate_html_words(s, num, end_text='...'):
    """Truncates HTML to a certain number of words (not counting tags and
    comments). Closes opened tags if they were correctly closed in the given
    html. Takes an optional argument of what should be used to notify that the
    string has been truncated, defaulting to ellipsis (...).

    Newlines in the HTML are preserved.
    """
    s = force_unicode(s)
    length = int(num)
    if length <= 0:
        return u''
    html4_singlets = ('br', 'col', 'link', 'base', 'img', 'param', 'area', 'hr', 'input')
    # Set up regular expressions
    re_words = re.compile(r'&.*?;|<.*?>|(\w[\w-]*)', re.U)
    re_tag = re.compile(r'<(/)?([^ ]+?)(?: (/)| .*?)?>')
    # Count non-HTML words and keep note of open tags
    pos = 0
    end_text_pos = 0
    words = 0
    open_tags = []
    while words <= length:
        m = re_words.search(s, pos)
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
        tagname = tagname.lower()  # Element names are always case-insensitive
        if self_closing or tagname in html4_singlets:
            pass
        elif closing_tag:
            # Check for match in open tags list
            try:
                i = open_tags.index(tagname)
            except ValueError:
                pass
            else:
                # SGML: An end tag closes, back to the matching start tag, all unclosed intervening start tags with omitted end tags
                open_tags = open_tags[i+1:]
        else:
            # Add it to the start of the open tags list
            open_tags.insert(0, tagname)
    if words <= length:
        # Don't try to close tags if we don't need to truncate
        return s
    out = s[:end_text_pos]
    if end_text:
        out += ' ' + end_text
    # Close any tags still open
    for tag in open_tags:
        out += '</%s>' % tag
    # Return string
    return out
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
    return u'%s %s %s' % (', '.join([force_unicode(i) for i in list_][:-1]), force_unicode(last_word), force_unicode(list_[-1]))
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
    import cStringIO, gzip
    zbuf = cStringIO.StringIO()
    zfile = gzip.GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
    zfile.write(s)
    zfile.close()
    return zbuf.getvalue()

ustring_re = re.compile(u"([\u0080-\uffff])")

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
