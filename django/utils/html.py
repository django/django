"""HTML utilities suitable for global use."""

import re
import string

from django.utils.safestring import SafeData, mark_safe
from django.utils.encoding import force_unicode
from django.utils.functional import allow_lazy
from django.utils.http import urlquote

# Configuration for urlize() function.
LEADING_PUNCTUATION  = ['(', '<', '&lt;']
TRAILING_PUNCTUATION = ['.', ',', ')', '>', '\n', '&gt;']

# List of possible strings used for bullets in bulleted lists.
DOTS = ['&middot;', '*', '\xe2\x80\xa2', '&#149;', '&bull;', '&#8226;']

unencoded_ampersands_re = re.compile(r'&(?!(\w+|#\d+);)')
word_split_re = re.compile(r'(\s+)')
punctuation_re = re.compile('^(?P<lead>(?:%s)*)(?P<middle>.*?)(?P<trail>(?:%s)*)$' % \
    ('|'.join([re.escape(x) for x in LEADING_PUNCTUATION]),
    '|'.join([re.escape(x) for x in TRAILING_PUNCTUATION])))
simple_email_re = re.compile(r'^\S+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+$')
link_target_attribute_re = re.compile(r'(<a [^>]*?)target=[^\s>]+')
html_gunk_re = re.compile(r'(?:<br clear="all">|<i><\/i>|<b><\/b>|<em><\/em>|<strong><\/strong>|<\/?smallcaps>|<\/?uppercase>)', re.IGNORECASE)
hard_coded_bullets_re = re.compile(r'((?:<p>(?:%s).*?[a-zA-Z].*?</p>\s*)+)' % '|'.join([re.escape(x) for x in DOTS]), re.DOTALL)
trailing_empty_content_re = re.compile(r'(?:<p>(?:&nbsp;|\s|<br \/>)*?</p>\s*)+\Z')
del x # Temporary variable

def escape(html):
    """Returns the given HTML with ampersands, quotes and carets encoded."""
    return mark_safe(force_unicode(html).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;'))
escape = allow_lazy(escape, unicode)

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
    value = re.sub(r'\r\n|\r|\n', '\n', force_unicode(value)) # normalize newlines
    paras = re.split('\n{2,}', value)
    if autoescape:
        paras = [u'<p>%s</p>' % escape(p.strip()).replace('\n', '<br />') for p in paras]
    else:
        paras = [u'<p>%s</p>' % p.strip().replace('\n', '<br />') for p in paras]
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

def urlize(text, trim_url_limit=None, nofollow=False, autoescape=False):
    """
    Converts any URLs in text into clickable links.

    Works on http://, https://, and www. links.  Links can have trailing
    punctuation (periods, commas, close-parens) and leading punctuation
    (opening parens) and it'll still do the right thing.

    If trim_url_limit is not None, the URLs in link text longer than this limit
    will truncated to trim_url_limit-3 characters and appended with an elipsis.

    If nofollow is True, the URLs in link text will get a rel="nofollow"
    attribute.
    """
    if autoescape:
        trim_url = lambda x, limit=trim_url_limit: conditional_escape(limit is not None and (len(x) > limit and ('%s...' % x[:max(0, limit - 3)])) or x)
    else:
        trim_url = lambda x, limit=trim_url_limit: limit is not None and (len(x) > limit and ('%s...' % x[:max(0, limit - 3)])) or x
    safe_input = isinstance(text, SafeData)
    words = word_split_re.split(force_unicode(text))
    nofollow_attr = nofollow and ' rel="nofollow"' or ''
    for i, word in enumerate(words):
        match = punctuation_re.match(word)
        if match:
            lead, middle, trail = match.groups()
            if safe_input:
                middle = mark_safe(middle)
            if middle.startswith('www.') or ('@' not in middle and not middle.startswith('http://') and \
                    len(middle) > 0 and middle[0] in string.ascii_letters + string.digits and \
                    (middle.endswith('.org') or middle.endswith('.net') or middle.endswith('.com'))):
                middle = 'http://%s' % middle
            if middle.startswith('http://') or middle.startswith('https://'):
                url = urlquote(middle, safe='/&=:;#?+*')
                if autoescape and not safe_input:
                    url = escape(url)
                trimmed_url = trim_url(middle)
                middle = '<a href="%s"%s>%s</a>' % (url, nofollow_attr,
                        trimmed_url)
            elif '@' in middle and not middle.startswith('www.') and \
                      not ':' in middle and simple_email_re.match(middle):
                if autoescape:
                    middle = conditional_escape(middle)
                middle = '<a href="mailto:%s">%s</a>' % (middle, middle)
            if lead + middle + trail != word:
                if autoescape and not safe_input:
                    lead, trail = escape(lead), escape(trail)
                words[i] = mark_safe('%s%s%s' % (lead, middle, trail))
            elif autoescape and not safe_input:
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
        s = match.group().replace('</p>', '</li>')
        for d in DOTS:
            s = s.replace('<p>%s' % d, '<li>')
        return u'<ul>\n%s\n</ul>' % s
    text = hard_coded_bullets_re.sub(replace_p_tags, text)
    # Remove stuff like "<p>&nbsp;&nbsp;</p>", but only if it's at the bottom
    # of the text.
    text = trailing_empty_content_re.sub('', text)
    return text
clean_html = allow_lazy(clean_html, unicode)
