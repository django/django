"""HTML utilities suitable for global use."""

import re
import string
import urllib
import urlparse

from django.utils.safestring import SafeData, mark_safe
from django.utils.encoding import smart_str, force_unicode
from django.utils.functional import allow_lazy
from django.utils.text import normalize_newlines

# Configuration for urlize() function.
TRAILING_PUNCTUATION = ['.', ',', ':', ';']
WRAPPING_PUNCTUATION = [('(', ')'), ('<', '>'), ('&lt;', '&gt;')]

# List of possible strings used for bullets in bulleted lists.
DOTS = [u'&middot;', u'*', u'\u2022', u'&#149;', u'&bull;', u'&#8226;']

unencoded_ampersands_re = re.compile(r'&(?!(\w+|#\d+);)')
unquoted_percents_re = re.compile(r'%(?![0-9A-Fa-f]{2})')
word_split_re = re.compile(r'(\s+)')
simple_url_re = re.compile(r'^https?://\w')
simple_url_2_re = re.compile(r'^www\.|^(?!http)\w[^@]+\.(com|edu|gov|int|mil|net|org)$')
simple_email_re = re.compile(r'^\S+@\S+\.\S+$')
link_target_attribute_re = re.compile(r'(<a [^>]*?)target=[^\s>]+')
html_gunk_re = re.compile(r'(?:<br clear="all">|<i><\/i>|<b><\/b>|<em><\/em>|<strong><\/strong>|<\/?smallcaps>|<\/?uppercase>)', re.IGNORECASE)
hard_coded_bullets_re = re.compile(r'((?:<p>(?:%s).*?[a-zA-Z].*?</p>\s*)+)' % '|'.join([re.escape(x) for x in DOTS]), re.DOTALL)
trailing_empty_content_re = re.compile(r'(?:<p>(?:&nbsp;|\s|<br \/>)*?</p>\s*)+\Z')
del x # Temporary variable

def escape(html):
    """
    Returns the given HTML with ampersands, quotes and angle brackets encoded.
    """
    return mark_safe(force_unicode(html).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;'))
escape = allow_lazy(escape, unicode)

_base_js_escapes = (
    ('\\', r'\u005C'),
    ('\'', r'\u0027'),
    ('"', r'\u0022'),
    ('>', r'\u003E'),
    ('<', r'\u003C'),
    ('&', r'\u0026'),
    ('=', r'\u003D'),
    ('-', r'\u002D'),
    (';', r'\u003B'),
    (u'\u2028', r'\u2028'),
    (u'\u2029', r'\u2029')
)

# Escape every ASCII character with a value less than 32.
_js_escapes = (_base_js_escapes +
               tuple([('%c' % z, '\\u%04X' % z) for z in range(32)]))

def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    for bad, good in _js_escapes:
        value = mark_safe(force_unicode(value).replace(bad, good))
    return value
escapejs = allow_lazy(escapejs, unicode)

def conditional_escape(html):
    """
    Similar to escape(), except that it doesn't operate on pre-escaped strings.
    """
    if isinstance(html, SafeData):
        return html
    else:
        return escape(html)

def linebreaks(value, autoescape=False):
    """Converts newlines into <p> and <br />s."""
    value = normalize_newlines(value)
    paras = re.split('\n{2,}', value)
    if autoescape:
        paras = [u'<p>%s</p>' % escape(p).replace('\n', '<br />') for p in paras]
    else:
        paras = [u'<p>%s</p>' % p.replace('\n', '<br />') for p in paras]
    return u'\n\n'.join(paras)
linebreaks = allow_lazy(linebreaks, unicode)

def strip_tags(value):
    """Returns the given HTML with all tags stripped."""
    return re.sub(r'<[^>]*?>', '', force_unicode(value))
strip_tags = allow_lazy(strip_tags)

def strip_spaces_between_tags(value):
    """Returns the given HTML with spaces between tags removed."""
    return re.sub(r'>\s+<', '><', force_unicode(value))
strip_spaces_between_tags = allow_lazy(strip_spaces_between_tags, unicode)

def strip_entities(value):
    """Returns the given HTML with all entities (&something;) stripped."""
    return re.sub(r'&(?:\w+|#\d+);', '', force_unicode(value))
strip_entities = allow_lazy(strip_entities, unicode)

def fix_ampersands(value):
    """Returns the given HTML with all unencoded ampersands encoded correctly."""
    return unencoded_ampersands_re.sub('&amp;', force_unicode(value))
fix_ampersands = allow_lazy(fix_ampersands, unicode)

def smart_urlquote(url):
    "Quotes a URL if it isn't already quoted."
    # Handle IDN before quoting.
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    try:
        netloc = netloc.encode('idna') # IDN -> ACE
    except UnicodeError: # invalid domain part
        pass
    else:
        url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    # An URL is considered unquoted if it contains no % characters or
    # contains a % not followed by two hexadecimal digits. See #9655.
    if '%' not in url or unquoted_percents_re.search(url):
        # See http://bugs.python.org/issue2637
        url = urllib.quote(smart_str(url), safe='!*\'();:@&=+$,/?#[]~')

    return force_unicode(url)

def urlize(text, trim_url_limit=None, nofollow=False, autoescape=False):
    """
    Converts any URLs in text into clickable links.

    Works on http://, https://, www. links, and also on links ending in one of
    the original seven gTLDs (.com, .edu, .gov, .int, .mil, .net, and .org).
    Links can have trailing punctuation (periods, commas, close-parens) and
    leading punctuation (opening parens) and it'll still do the right thing.

    If trim_url_limit is not None, the URLs in link text longer than this limit
    will truncated to trim_url_limit-3 characters and appended with an elipsis.

    If nofollow is True, the URLs in link text will get a rel="nofollow"
    attribute.

    If autoescape is True, the link text and URLs will get autoescaped.
    """
    trim_url = lambda x, limit=trim_url_limit: limit is not None and (len(x) > limit and ('%s...' % x[:max(0, limit - 3)])) or x
    safe_input = isinstance(text, SafeData)
    words = word_split_re.split(force_unicode(text))
    for i, word in enumerate(words):
        match = None
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
                url = smart_urlquote(middle)
            elif simple_url_2_re.match(middle):
                url = smart_urlquote('http://%s' % middle)
            elif not ':' in middle and simple_email_re.match(middle):
                local, domain = middle.rsplit('@', 1)
                try:
                    domain = domain.encode('idna')
                except UnicodeError:
                    continue
                url = 'mailto:%s@%s' % (local, domain)
                nofollow_attr = ''

            # Make link.
            if url:
                trimmed = trim_url(middle)
                if autoescape and not safe_input:
                    lead, trail = escape(lead), escape(trail)
                    url, trimmed = escape(url), escape(trimmed)
                middle = '<a href="%s"%s>%s</a>' % (url, nofollow_attr, trimmed)
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
    return u''.join(words)
urlize = allow_lazy(urlize, unicode)

def clean_html(text):
    """
    Clean the given HTML.  Specifically, do the following:
        * Convert <b> and <i> to <strong> and <em>.
        * Encode all ampersands correctly.
        * Remove all "target" attributes from <a> tags.
        * Remove extraneous HTML, such as presentational tags that open and
          immediately close and <br clear="all">.
        * Convert hard-coded bullets into HTML unordered lists.
        * Remove stuff like "<p>&nbsp;&nbsp;</p>", but only if it's at the
          bottom of the text.
    """
    from django.utils.text import normalize_newlines
    text = normalize_newlines(force_unicode(text))
    text = re.sub(r'<(/?)\s*b\s*>', '<\\1strong>', text)
    text = re.sub(r'<(/?)\s*i\s*>', '<\\1em>', text)
    text = fix_ampersands(text)
    # Remove all target="" attributes from <a> tags.
    text = link_target_attribute_re.sub('\\1', text)
    # Trim stupid HTML such as <br clear="all">.
    text = html_gunk_re.sub('', text)
    # Convert hard-coded bullets into HTML unordered lists.
    def replace_p_tags(match):
        s = match.group().replace(u'</p>', u'</li>')
        for d in DOTS:
            s = s.replace(u'<p>%s' % d, u'<li>')
        return u'<ul>\n%s\n</ul>' % s
    text = hard_coded_bullets_re.sub(replace_p_tags, text)
    # Remove stuff like "<p>&nbsp;&nbsp;</p>", but only if it's at the bottom
    # of the text.
    text = trailing_empty_content_re.sub(u'', text)
    return text
clean_html = allow_lazy(clean_html, unicode)
