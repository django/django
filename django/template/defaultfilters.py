"""Default variable filters."""

import re

try:
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
except ImportError:
    from django.utils._decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import random as random_module
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

from django.template import Variable, Library
from django.conf import settings
from django.utils.translation import ugettext, ungettext
from django.utils.encoding import force_unicode, iri_to_uri
from django.utils.safestring import mark_safe, SafeData

register = Library()

#######################
# STRING DECORATOR    #
#######################

def stringfilter(func):
    """
    Decorator for filters which should only receive unicode objects. The object
    passed as the first positional argument will be converted to a unicode
    object.
    """
    def _dec(*args, **kwargs):
        if args:
            args = list(args)
            args[0] = force_unicode(args[0])
            if isinstance(args[0], SafeData) and getattr(func, 'is_safe', False):
                return mark_safe(func(*args, **kwargs))
        return func(*args, **kwargs)

    # Include a reference to the real function (used to check original
    # arguments by the template parser).
    _dec._decorated_function = getattr(func, '_decorated_function', func)
    for attr in ('is_safe', 'needs_autoescape'):
        if hasattr(func, attr):
            setattr(_dec, attr, getattr(func, attr))
    return wraps(func)(_dec)

###################
# STRINGS         #
###################

def addslashes(value):
    """
    Adds slashes before quotes. Useful for escaping strings in CSV, for
    example. Less useful for escaping JavaScript; use the ``escapejs``
    filter instead.
    """
    return value.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
addslashes.is_safe = True
addslashes = stringfilter(addslashes)

def capfirst(value):
    """Capitalizes the first character of the value."""
    return value and value[0].upper() + value[1:]
capfirst.is_safe=True
capfirst = stringfilter(capfirst)

_base_js_escapes = (
    ('\\', r'\x5C'),
    ('\'', r'\x27'),
    ('"', r'\x22'),
    ('>', r'\x3E'),
    ('<', r'\x3C'),
    ('&', r'\x26'),
    ('=', r'\x3D'),
    ('-', r'\x2D'),
    (';', r'\x3B')
)

# Escape every ASCII character with a value less than 32.
_js_escapes = (_base_js_escapes +
               tuple([('%c' % z, '\\x%02X' % z) for z in range(32)]))

def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    for bad, good in _js_escapes:
        value = value.replace(bad, good)
    return value
escapejs = stringfilter(escapejs)

def fix_ampersands(value):
    """Replaces ampersands with ``&amp;`` entities."""
    from django.utils.html import fix_ampersands
    return fix_ampersands(value)
fix_ampersands.is_safe=True
fix_ampersands = stringfilter(fix_ampersands)

# Values for testing floatformat input against infinity and NaN representations,
# which differ across platforms and Python versions.  Some (i.e. old Windows
# ones) are not recognized by Decimal but we want to return them unchanged vs.
# returning an empty string as we do for completley invalid input.  Note these
# need to be built up from values that are not inf/nan, since inf/nan values do
# not reload properly from .pyc files on Windows prior to some level of Python 2.5
# (see Python Issue757815 and Issue1080440).
pos_inf = 1e200 * 1e200
neg_inf = -1e200 * 1e200
nan = (1e200 * 1e200) / (1e200 * 1e200)
special_floats = [str(pos_inf), str(neg_inf), str(nan)]

def floatformat(text, arg=-1):
    """
    Displays a float to a specified number of decimal places.

    If called without an argument, it displays the floating point number with
    one decimal place -- but only if there's a decimal place to be displayed:

    * num1 = 34.23234
    * num2 = 34.00000
    * num3 = 34.26000
    * {{ num1|floatformat }} displays "34.2"
    * {{ num2|floatformat }} displays "34"
    * {{ num3|floatformat }} displays "34.3"

    If arg is positive, it will always display exactly arg number of decimal
    places:

    * {{ num1|floatformat:3 }} displays "34.232"
    * {{ num2|floatformat:3 }} displays "34.000"
    * {{ num3|floatformat:3 }} displays "34.260"

    If arg is negative, it will display arg number of decimal places -- but
    only if there are places to be displayed:

    * {{ num1|floatformat:"-3" }} displays "34.232"
    * {{ num2|floatformat:"-3" }} displays "34"
    * {{ num3|floatformat:"-3" }} displays "34.260"

    If the input float is infinity or NaN, the (platform-dependent) string
    representation of that value will be displayed.
    """

    try:
        input_val = force_unicode(text)
        d = Decimal(input_val)
    except UnicodeEncodeError:
        return u''
    except InvalidOperation:
        if input_val in special_floats:
            return input_val
        else:
            return u''
    try:
        p = int(arg)
    except ValueError:
        return input_val

    try:
        m = int(d) - d
    except (OverflowError, InvalidOperation):
        return input_val

    if not m and p < 0:
        return mark_safe(u'%d' % (int(d)))

    if p == 0:
        exp = Decimal(1)
    else:
        exp = Decimal('1.0') / (Decimal(10) ** abs(p))
    try:
        return mark_safe(u'%s' % str(d.quantize(exp, ROUND_HALF_UP)))
    except InvalidOperation:
        return input_val
floatformat.is_safe = True

def iriencode(value):
    """Escapes an IRI value for use in a URL."""
    return force_unicode(iri_to_uri(value))
iriencode.is_safe = True
iriencode = stringfilter(iriencode)

def linenumbers(value, autoescape=None):
    """Displays text with line numbers."""
    from django.utils.html import escape
    lines = value.split(u'\n')
    # Find the maximum width of the line count, for use with zero padding
    # string format command
    width = unicode(len(unicode(len(lines))))
    if not autoescape or isinstance(value, SafeData):
        for i, line in enumerate(lines):
            lines[i] = (u"%0" + width  + u"d. %s") % (i + 1, line)
    else:
        for i, line in enumerate(lines):
            lines[i] = (u"%0" + width  + u"d. %s") % (i + 1, escape(line))
    return mark_safe(u'\n'.join(lines))
linenumbers.is_safe = True
linenumbers.needs_autoescape = True
linenumbers = stringfilter(linenumbers)

def lower(value):
    """Converts a string into all lowercase."""
    return value.lower()
lower.is_safe = True
lower = stringfilter(lower)

def make_list(value):
    """
    Returns the value turned into a list.

    For an integer, it's a list of digits.
    For a string, it's a list of characters.
    """
    return list(value)
make_list.is_safe = False
make_list = stringfilter(make_list)

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return mark_safe(re.sub('[-\s]+', '-', value))
slugify.is_safe = True
slugify = stringfilter(slugify)

def stringformat(value, arg):
    """
    Formats the variable according to the arg, a string formatting specifier.

    This specifier uses Python string formating syntax, with the exception that
    the leading "%" is dropped.

    See http://docs.python.org/lib/typesseq-strings.html for documentation
    of Python string formatting
    """
    try:
        return (u"%" + unicode(arg)) % value
    except (ValueError, TypeError):
        return u""
stringformat.is_safe = True

def title(value):
    """Converts a string into titlecase."""
    return re.sub("([a-z])'([A-Z])", lambda m: m.group(0).lower(), value.title())
title.is_safe = True
title = stringfilter(title)

def truncatewords(value, arg):
    """
    Truncates a string after a certain number of words.

    Argument: Number of words to truncate after.
    """
    from django.utils.text import truncate_words
    try:
        length = int(arg)
    except ValueError: # Invalid literal for int().
        return value # Fail silently.
    return truncate_words(value, length)
truncatewords.is_safe = True
truncatewords = stringfilter(truncatewords)

def truncatewords_html(value, arg):
    """
    Truncates HTML after a certain number of words.

    Argument: Number of words to truncate after.
    """
    from django.utils.text import truncate_html_words
    try:
        length = int(arg)
    except ValueError: # invalid literal for int()
        return value # Fail silently.
    return truncate_html_words(value, length)
truncatewords_html.is_safe = True
truncatewords_html = stringfilter(truncatewords_html)

def upper(value):
    """Converts a string into all uppercase."""
    return value.upper()
upper.is_safe = False
upper = stringfilter(upper)

def urlencode(value):
    """Escapes a value for use in a URL."""
    from django.utils.http import urlquote
    return urlquote(value)
urlencode.is_safe = False
urlencode = stringfilter(urlencode)

def urlize(value, autoescape=None):
    """Converts URLs in plain text into clickable links."""
    from django.utils.html import urlize
    return mark_safe(urlize(value, nofollow=True, autoescape=autoescape))
urlize.is_safe=True
urlize.needs_autoescape = True
urlize = stringfilter(urlize)

def urlizetrunc(value, limit, autoescape=None):
    """
    Converts URLs into clickable links, truncating URLs to the given character
    limit, and adding 'rel=nofollow' attribute to discourage spamming.

    Argument: Length to truncate URLs to.
    """
    from django.utils.html import urlize
    return mark_safe(urlize(value, trim_url_limit=int(limit), nofollow=True,
                            autoescape=autoescape))
urlizetrunc.is_safe = True
urlizetrunc.needs_autoescape = True
urlizetrunc = stringfilter(urlizetrunc)

def wordcount(value):
    """Returns the number of words."""
    return len(value.split())
wordcount.is_safe = False
wordcount = stringfilter(wordcount)

def wordwrap(value, arg):
    """
    Wraps words at specified line length.

    Argument: number of characters to wrap the text at.
    """
    from django.utils.text import wrap
    return wrap(value, int(arg))
wordwrap.is_safe = True
wordwrap = stringfilter(wordwrap)

def ljust(value, arg):
    """
    Left-aligns the value in a field of a given width.

    Argument: field size.
    """
    return value.ljust(int(arg))
ljust.is_safe = True
ljust = stringfilter(ljust)

def rjust(value, arg):
    """
    Right-aligns the value in a field of a given width.

    Argument: field size.
    """
    return value.rjust(int(arg))
rjust.is_safe = True
rjust = stringfilter(rjust)

def center(value, arg):
    """Centers the value in a field of a given width."""
    return value.center(int(arg))
center.is_safe = True
center = stringfilter(center)

def cut(value, arg):
    """
    Removes all values of arg from the given string.
    """
    safe = isinstance(value, SafeData)
    value = value.replace(arg, u'')
    if safe and arg != ';':
        return mark_safe(value)
    return value
cut = stringfilter(cut)

###################
# HTML STRINGS    #
###################

def escape(value):
    """
    Marks the value as a string that should not be auto-escaped.
    """
    from django.utils.safestring import mark_for_escaping
    return mark_for_escaping(value)
escape.is_safe = True
escape = stringfilter(escape)

def force_escape(value):
    """
    Escapes a string's HTML. This returns a new string containing the escaped
    characters (as opposed to "escape", which marks the content for later
    possible escaping).
    """
    from django.utils.html import escape
    return mark_safe(escape(value))
force_escape = stringfilter(force_escape)
force_escape.is_safe = True

def linebreaks(value, autoescape=None):
    """
    Replaces line breaks in plain text with appropriate HTML; a single
    newline becomes an HTML line break (``<br />``) and a new line
    followed by a blank line becomes a paragraph break (``</p>``).
    """
    from django.utils.html import linebreaks
    autoescape = autoescape and not isinstance(value, SafeData)
    return mark_safe(linebreaks(value, autoescape))
linebreaks.is_safe = True
linebreaks.needs_autoescape = True
linebreaks = stringfilter(linebreaks)

def linebreaksbr(value, autoescape=None):
    """
    Converts all newlines in a piece of plain text to HTML line breaks
    (``<br />``).
    """
    if autoescape and not isinstance(value, SafeData):
        from django.utils.html import escape
        value = escape(value)
    return mark_safe(value.replace('\n', '<br />'))
linebreaksbr.is_safe = True
linebreaksbr.needs_autoescape = True
linebreaksbr = stringfilter(linebreaksbr)

def safe(value):
    """
    Marks the value as a string that should not be auto-escaped.
    """
    from django.utils.safestring import mark_safe
    return mark_safe(value)
safe.is_safe = True
safe = stringfilter(safe)

def removetags(value, tags):
    """Removes a space separated list of [X]HTML tags from the output."""
    tags = [re.escape(tag) for tag in tags.split()]
    tags_re = u'(%s)' % u'|'.join(tags)
    starttag_re = re.compile(ur'<%s(/?>|(\s+[^>]*>))' % tags_re, re.U)
    endtag_re = re.compile(u'</%s>' % tags_re)
    value = starttag_re.sub(u'', value)
    value = endtag_re.sub(u'', value)
    return value
removetags.is_safe = True
removetags = stringfilter(removetags)

def striptags(value):
    """Strips all [X]HTML tags."""
    from django.utils.html import strip_tags
    return strip_tags(value)
striptags.is_safe = True
striptags = stringfilter(striptags)

###################
# LISTS           #
###################

def dictsort(value, arg):
    """
    Takes a list of dicts, returns that list sorted by the property given in
    the argument.
    """
    var_resolve = Variable(arg).resolve
    decorated = [(var_resolve(item), item) for item in value]
    decorated.sort()
    return [item[1] for item in decorated]
dictsort.is_safe = False

def dictsortreversed(value, arg):
    """
    Takes a list of dicts, returns that list sorted in reverse order by the
    property given in the argument.
    """
    var_resolve = Variable(arg).resolve
    decorated = [(var_resolve(item), item) for item in value]
    decorated.sort()
    decorated.reverse()
    return [item[1] for item in decorated]
dictsortreversed.is_safe = False

def first(value):
    """Returns the first item in a list."""
    try:
        return value[0]
    except IndexError:
        return u''
first.is_safe = False

def join(value, arg, autoescape=None):
    """
    Joins a list with a string, like Python's ``str.join(list)``.
    """
    if autoescape:
        from django.utils.html import conditional_escape
        value = [conditional_escape(v) for v in value]
    try:
        data = arg.join(value)
    except AttributeError: # fail silently but nicely
        return value
    return mark_safe(data)
join.is_safe = True
join.needs_autoescape = True

def last(value):
    "Returns the last item in a list"
    try:
        return value[-1]
    except IndexError:
        return u''
last.is_safe = True

def length(value):
    """Returns the length of the value - useful for lists."""
    return len(value)
length.is_safe = True

def length_is(value, arg):
    """Returns a boolean of whether the value's length is the argument."""
    return len(value) == int(arg)
length_is.is_safe = False

def random(value):
    """Returns a random item from the list."""
    return random_module.choice(value)
random.is_safe = True

def slice_(value, arg):
    """
    Returns a slice of the list.

    Uses the same syntax as Python's list slicing; see
    http://diveintopython.org/native_data_types/lists.html#odbchelper.list.slice
    for an introduction.
    """
    try:
        bits = []
        for x in arg.split(u':'):
            if len(x) == 0:
                bits.append(None)
            else:
                bits.append(int(x))
        return value[slice(*bits)]

    except (ValueError, TypeError):
        return value # Fail silently.
slice_.is_safe = True

def unordered_list(value, autoescape=None):
    """
    Recursively takes a self-nested list and returns an HTML unordered list --
    WITHOUT opening and closing <ul> tags.

    The list is assumed to be in the proper format. For example, if ``var``
    contains: ``['States', ['Kansas', ['Lawrence', 'Topeka'], 'Illinois']]``,
    then ``{{ var|unordered_list }}`` would return::

        <li>States
        <ul>
                <li>Kansas
                <ul>
                        <li>Lawrence</li>
                        <li>Topeka</li>
                </ul>
                </li>
                <li>Illinois</li>
        </ul>
        </li>
    """
    if autoescape:
        from django.utils.html import conditional_escape
        escaper = conditional_escape
    else:
        escaper = lambda x: x
    def convert_old_style_list(list_):
        """
        Converts old style lists to the new easier to understand format.

        The old list format looked like:
            ['Item 1', [['Item 1.1', []], ['Item 1.2', []]]

        And it is converted to:
            ['Item 1', ['Item 1.1', 'Item 1.2]]
        """
        if not isinstance(list_, (tuple, list)) or len(list_) != 2:
            return list_, False
        first_item, second_item = list_
        if second_item == []:
            return [first_item], True
        old_style_list = True
        new_second_item = []
        for sublist in second_item:
            item, old_style_list = convert_old_style_list(sublist)
            if not old_style_list:
                break
            new_second_item.extend(item)
        if old_style_list:
            second_item = new_second_item
        return [first_item, second_item], old_style_list
    def _helper(list_, tabs=1):
        indent = u'\t' * tabs
        output = []

        list_length = len(list_)
        i = 0
        while i < list_length:
            title = list_[i]
            sublist = ''
            sublist_item = None
            if isinstance(title, (list, tuple)):
                sublist_item = title
                title = ''
            elif i < list_length - 1:
                next_item = list_[i+1]
                if next_item and isinstance(next_item, (list, tuple)):
                    # The next item is a sub-list.
                    sublist_item = next_item
                    # We've processed the next item now too.
                    i += 1
            if sublist_item:
                sublist = _helper(sublist_item, tabs+1)
                sublist = '\n%s<ul>\n%s\n%s</ul>\n%s' % (indent, sublist,
                                                         indent, indent)
            output.append('%s<li>%s%s</li>' % (indent,
                    escaper(force_unicode(title)), sublist))
            i += 1
        return '\n'.join(output)
    value, converted = convert_old_style_list(value)
    return mark_safe(_helper(value))
unordered_list.is_safe = True
unordered_list.needs_autoescape = True

###################
# INTEGERS        #
###################

def add(value, arg):
    """Adds the arg to the value."""
    return int(value) + int(arg)
add.is_safe = False

def get_digit(value, arg):
    """
    Given a whole number, returns the requested digit of it, where 1 is the
    right-most digit, 2 is the second-right-most digit, etc. Returns the
    original value for invalid input (if input or argument is not an integer,
    or if argument is less than 1). Otherwise, output is always an integer.
    """
    try:
        arg = int(arg)
        value = int(value)
    except ValueError:
        return value # Fail silently for an invalid argument
    if arg < 1:
        return value
    try:
        return int(str(value)[-arg])
    except IndexError:
        return 0
get_digit.is_safe = False

###################
# DATES           #
###################

def date(value, arg=None):
    """Formats a date according to the given format."""
    from django.utils.dateformat import format
    if not value:
        return u''
    if arg is None:
        arg = settings.DATE_FORMAT
    return format(value, arg)
date.is_safe = False

def time(value, arg=None):
    """Formats a time according to the given format."""
    from django.utils.dateformat import time_format
    if value in (None, u''):
        return u''
    if arg is None:
        arg = settings.TIME_FORMAT
    return time_format(value, arg)
time.is_safe = False

def timesince(value, arg=None):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    from django.utils.timesince import timesince
    if not value:
        return u''
    try:
        if arg:
            return timesince(value, arg)
        return timesince(value)
    except (ValueError, TypeError):
        return u''
timesince.is_safe = False

def timeuntil(value, arg=None):
    """Formats a date as the time until that date (i.e. "4 days, 6 hours")."""
    from django.utils.timesince import timeuntil
    from datetime import datetime
    if not value:
        return u''
    try:
        return timeuntil(value, arg)
    except (ValueError, TypeError):
        return u''
timeuntil.is_safe = False

###################
# LOGIC           #
###################

def default(value, arg):
    """If value is unavailable, use given default."""
    return value or arg
default.is_safe = False

def default_if_none(value, arg):
    """If value is None, use given default."""
    if value is None:
        return arg
    return value
default_if_none.is_safe = False

def divisibleby(value, arg):
    """Returns True if the value is devisible by the argument."""
    return int(value) % int(arg) == 0
divisibleby.is_safe = False

def yesno(value, arg=None):
    """
    Given a string mapping values for true, false and (optionally) None,
    returns one of those strings accoding to the value:

    ==========  ======================  ==================================
    Value       Argument                Outputs
    ==========  ======================  ==================================
    ``True``    ``"yeah,no,maybe"``     ``yeah``
    ``False``   ``"yeah,no,maybe"``     ``no``
    ``None``    ``"yeah,no,maybe"``     ``maybe``
    ``None``    ``"yeah,no"``           ``"no"`` (converts None to False
                                        if no mapping for None is given.
    ==========  ======================  ==================================
    """
    if arg is None:
        arg = ugettext('yes,no,maybe')
    bits = arg.split(u',')
    if len(bits) < 2:
        return value # Invalid arg.
    try:
        yes, no, maybe = bits
    except ValueError:
        # Unpack list of wrong size (no "maybe" value provided).
        yes, no, maybe = bits[0], bits[1], bits[1]
    if value is None:
        return maybe
    if value:
        return yes
    return no
yesno.is_safe = False

###################
# MISC            #
###################

def filesizeformat(bytes):
    """
    Formats the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
    102 bytes, etc).
    """
    try:
        bytes = float(bytes)
    except TypeError:
        return u"0 bytes"

    if bytes < 1024:
        return ungettext("%(size)d byte", "%(size)d bytes", bytes) % {'size': bytes}
    if bytes < 1024 * 1024:
        return ugettext("%.1f KB") % (bytes / 1024)
    if bytes < 1024 * 1024 * 1024:
        return ugettext("%.1f MB") % (bytes / (1024 * 1024))
    return ugettext("%.1f GB") % (bytes / (1024 * 1024 * 1024))
filesizeformat.is_safe = True

def pluralize(value, arg=u's'):
    """
    Returns a plural suffix if the value is not 1. By default, 's' is used as
    the suffix:

    * If value is 0, vote{{ value|pluralize }} displays "0 votes".
    * If value is 1, vote{{ value|pluralize }} displays "1 vote".
    * If value is 2, vote{{ value|pluralize }} displays "2 votes".

    If an argument is provided, that string is used instead:

    * If value is 0, class{{ value|pluralize:"es" }} displays "0 classes".
    * If value is 1, class{{ value|pluralize:"es" }} displays "1 class".
    * If value is 2, class{{ value|pluralize:"es" }} displays "2 classes".

    If the provided argument contains a comma, the text before the comma is
    used for the singular case and the text after the comma is used for the
    plural case:

    * If value is 0, cand{{ value|pluralize:"y,ies" }} displays "0 candies".
    * If value is 1, cand{{ value|pluralize:"y,ies" }} displays "1 candy".
    * If value is 2, cand{{ value|pluralize:"y,ies" }} displays "2 candies".
    """
    if not u',' in arg:
        arg = u',' + arg
    bits = arg.split(u',')
    if len(bits) > 2:
        return u''
    singular_suffix, plural_suffix = bits[:2]

    try:
        if int(value) != 1:
            return plural_suffix
    except ValueError: # Invalid string that's not a number.
        pass
    except TypeError: # Value isn't a string or a number; maybe it's a list?
        try:
            if len(value) != 1:
                return plural_suffix
        except TypeError: # len() of unsized object.
            pass
    return singular_suffix
pluralize.is_safe = False

def phone2numeric(value):
    """Takes a phone number and converts it in to its numerical equivalent."""
    from django.utils.text import phone2numeric
    return phone2numeric(value)
phone2numeric.is_safe = True

def pprint(value):
    """A wrapper around pprint.pprint -- for debugging, really."""
    from pprint import pformat
    try:
        return pformat(value)
    except Exception, e:
        return u"Error in formatting: %s" % force_unicode(e, errors="replace")
pprint.is_safe = True

# Syntax: register.filter(name of filter, callback)
register.filter(add)
register.filter(addslashes)
register.filter(capfirst)
register.filter(center)
register.filter(cut)
register.filter(date)
register.filter(default)
register.filter(default_if_none)
register.filter(dictsort)
register.filter(dictsortreversed)
register.filter(divisibleby)
register.filter(escape)
register.filter(escapejs)
register.filter(filesizeformat)
register.filter(first)
register.filter(fix_ampersands)
register.filter(floatformat)
register.filter(force_escape)
register.filter(get_digit)
register.filter(iriencode)
register.filter(join)
register.filter(last)
register.filter(length)
register.filter(length_is)
register.filter(linebreaks)
register.filter(linebreaksbr)
register.filter(linenumbers)
register.filter(ljust)
register.filter(lower)
register.filter(make_list)
register.filter(phone2numeric)
register.filter(pluralize)
register.filter(pprint)
register.filter(removetags)
register.filter(random)
register.filter(rjust)
register.filter(safe)
register.filter('slice', slice_)
register.filter(slugify)
register.filter(stringformat)
register.filter(striptags)
register.filter(time)
register.filter(timesince)
register.filter(timeuntil)
register.filter(title)
register.filter(truncatewords)
register.filter(truncatewords_html)
register.filter(unordered_list)
register.filter(upper)
register.filter(urlencode)
register.filter(urlize)
register.filter(urlizetrunc)
register.filter(wordcount)
register.filter(wordwrap)
register.filter(yesno)
