"Default variable filters"

from django.template import resolve_variable, Library
from django.conf import settings
from django.utils.translation import ugettext
from django.utils.encoding import smart_unicode, smart_str
import re
import random as random_module

register = Library()

#######################
# STRING DECORATOR    #
#######################

def stringfilter(func):
    """
    Decorator for filters which should only receive unicode objects. The object passed
    as the first positional argument will be converted to a unicode object.
    """
    def _dec(*args, **kwargs):
        if args:
            args = list(args)
            args[0] = smart_unicode(args[0])
        return func(*args, **kwargs)

    # Include a reference to the real function (used to check original
    # arguments by the template parser).
    _dec._decorated_function = getattr(func, '_decorated_function', func)
    return _dec

###################
# STRINGS         #
###################


def addslashes(value):
    "Adds slashes - useful for passing strings to JavaScript, for example."
    return value.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
addslashes = stringfilter(addslashes)

def capfirst(value):
    "Capitalizes the first character of the value"
    return value and value[0].upper() + value[1:]
capfirst = stringfilter(capfirst)

def fix_ampersands(value):
    "Replaces ampersands with ``&amp;`` entities"
    from django.utils.html import fix_ampersands
    return fix_ampersands(value)
fix_ampersands = stringfilter(fix_ampersands)

def floatformat(text, arg=-1):
    """
    If called without an argument, displays a floating point
    number as 34.2 -- but only if there's a point to be displayed.
    With a positive numeric argument, it displays that many decimal places
    always.
    With a negative numeric argument, it will display that many decimal
    places -- but only if there's places to be displayed.
    Examples:

    * num1 = 34.23234
    * num2 = 34.00000
    * num1|floatformat results in 34.2
    * num2|floatformat is 34
    * num1|floatformat:3 is 34.232
    * num2|floatformat:3 is 34.000
    * num1|floatformat:-3 is 34.232
    * num2|floatformat:-3 is 34
    """
    try:
        f = float(text)
    except ValueError:
        return u''
    try:
        d = int(arg)
    except ValueError:
        return smart_unicode(f)
    m = f - int(f)
    if not m and d < 0:
        return u'%d' % int(f)
    else:
        formatstr = u'%%.%df' % abs(d)
        return formatstr % f

def linenumbers(value):
    "Displays text with line numbers"
    from django.utils.html import escape
    lines = value.split(u'\n')
    # Find the maximum width of the line count, for use with zero padding string format command
    width = unicode(len(unicode(len(lines))))
    for i, line in enumerate(lines):
        lines[i] = (u"%0" + width  + u"d. %s") % (i + 1, escape(line))
    return u'\n'.join(lines)
linenumbers = stringfilter(linenumbers)

def lower(value):
    "Converts a string into all lowercase"
    return value.lower()
lower = stringfilter(lower)

def make_list(value):
    """
    Returns the value turned into a list. For an integer, it's a list of
    digits. For a string, it's a list of characters.
    """
    return list(value)
make_list = stringfilter(make_list)

def slugify(value):
    "Converts to lowercase, removes non-alpha chars and converts spaces to hyphens"
    # Don't compile patterns as unicode because \w then would mean any letter. Slugify is effectively an asciiization.
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)
slugify = stringfilter(slugify)

def stringformat(value, arg):
    """
    Formats the variable according to the argument, a string formatting specifier.
    This specifier uses Python string formating syntax, with the exception that
    the leading "%" is dropped.

    See http://docs.python.org/lib/typesseq-strings.html for documentation
    of Python string formatting
    """
    try:
        return (u"%" + unicode(arg)) % value
    except (ValueError, TypeError):
        return u""

def title(value):
    "Converts a string into titlecase"
    return re.sub("([a-z])'([A-Z])", lambda m: m.group(0).lower(), value.title())
title = stringfilter(title)

def truncatewords(value, arg):
    """
    Truncates a string after a certain number of words

    Argument: Number of words to truncate after
    """
    from django.utils.text import truncate_words
    try:
        length = int(arg)
    except ValueError: # invalid literal for int()
        return value # Fail silently.
    return truncate_words(value, length)
truncatewords = stringfilter(truncatewords)

def truncatewords_html(value, arg):
    """
    Truncates HTML after a certain number of words

    Argument: Number of words to truncate after
    """
    from django.utils.text import truncate_html_words
    try:
        length = int(arg)
    except ValueError: # invalid literal for int()
        return value # Fail silently.
    return truncate_html_words(value, length)
truncatewords_html = stringfilter(truncatewords_html)

def upper(value):
    "Converts a string into all uppercase"
    return value.upper()
upper = stringfilter(upper)

def urlencode(value):
    "Escapes a value for use in a URL"
    import urllib
    return urllib.quote(value).decode('utf-8')
urlencode = stringfilter(urlencode)

def urlize(value):
    "Converts URLs in plain text into clickable links"
    from django.utils.html import urlize
    return urlize(value, nofollow=True)
urlize = stringfilter(urlize)

def urlizetrunc(value, limit):
    """
    Converts URLs into clickable links, truncating URLs to the given character limit,
    and adding 'rel=nofollow' attribute to discourage spamming.

    Argument: Length to truncate URLs to.
    """
    from django.utils.html import urlize
    return urlize(value, trim_url_limit=int(limit), nofollow=True)
urlizetrunc = stringfilter(urlizetrunc)

def wordcount(value):
    "Returns the number of words"
    return len(value.split())
wordcount = stringfilter(wordcount)

def wordwrap(value, arg):
    """
    Wraps words at specified line length

    Argument: number of characters to wrap the text at.
    """
    from django.utils.text import wrap
    return wrap(value, int(arg))
wordwrap = stringfilter(wordwrap)

def ljust(value, arg):
    """
    Left-aligns the value in a field of a given width

    Argument: field size
    """
    return value.ljust(int(arg))
ljust = stringfilter(ljust)

def rjust(value, arg):
    """
    Right-aligns the value in a field of a given width

    Argument: field size
    """
    return value.rjust(int(arg))
rjust = stringfilter(rjust)

def center(value, arg):
    "Centers the value in a field of a given width"
    return value.center(int(arg))
center = stringfilter(center)

def cut(value, arg):
    "Removes all values of arg from the given string"
    return value.replace(arg, u'')
cut = stringfilter(cut)

###################
# HTML STRINGS    #
###################

def escape(value):
    "Escapes a string's HTML"
    from django.utils.html import escape
    return escape(value)
escape = stringfilter(escape)

def linebreaks(value):
    "Converts newlines into <p> and <br />s"
    from django.utils.html import linebreaks
    return linebreaks(value)
linebreaks = stringfilter(linebreaks)

def linebreaksbr(value):
    "Converts newlines into <br />s"
    return value.replace('\n', '<br />')
linebreaksbr = stringfilter(linebreaksbr)

def removetags(value, tags):
    "Removes a space separated list of [X]HTML tags from the output"
    tags = [re.escape(tag) for tag in tags.split()]
    tags_re = u'(%s)' % u'|'.join(tags)
    starttag_re = re.compile(ur'<%s(/?>|(\s+[^>]*>))' % tags_re, re.U)
    endtag_re = re.compile(u'</%s>' % tags_re)
    value = starttag_re.sub(u'', value)
    value = endtag_re.sub(u'', value)
    return value
removetags = stringfilter(removetags)

def striptags(value):
    "Strips all [X]HTML tags"
    from django.utils.html import strip_tags
    return strip_tags(value)
striptags = stringfilter(striptags)

###################
# LISTS           #
###################

def dictsort(value, arg):
    """
    Takes a list of dicts, returns that list sorted by the property given in
    the argument.
    """
    decorated = [(resolve_variable(u'var.' + arg, {u'var' : item}), item) for item in value]
    decorated.sort()
    return [item[1] for item in decorated]

def dictsortreversed(value, arg):
    """
    Takes a list of dicts, returns that list sorted in reverse order by the
    property given in the argument.
    """
    decorated = [(resolve_variable(u'var.' + arg, {u'var' : item}), item) for item in value]
    decorated.sort()
    decorated.reverse()
    return [item[1] for item in decorated]

def first(value):
    "Returns the first item in a list"
    try:
        return value[0]
    except IndexError:
        return u''

def join(value, arg):
    "Joins a list with a string, like Python's ``str.join(list)``"
    try:
        return arg.join(map(smart_unicode, value))
    except AttributeError: # fail silently but nicely
        return value

def length(value):
    "Returns the length of the value - useful for lists"
    return len(value)

def length_is(value, arg):
    "Returns a boolean of whether the value's length is the argument"
    return len(value) == int(arg)

def random(value):
    "Returns a random item from the list"
    return random_module.choice(value)

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

def unordered_list(value):
    """
    Recursively takes a self-nested list and returns an HTML unordered list --
    WITHOUT opening and closing <ul> tags.

    The list is assumed to be in the proper format. For example, if ``var`` contains
    ``['States', [['Kansas', [['Lawrence', []], ['Topeka', []]]], ['Illinois', []]]]``,
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
    def _helper(value, tabs):
        indent = u'\t' * tabs
        if value[1]:
            return u'%s<li>%s\n%s<ul>\n%s\n%s</ul>\n%s</li>' % (indent, value[0], indent,
                u'\n'.join([_helper(v, tabs+1) for v in value[1]]), indent, indent)
        else:
            return u'%s<li>%s</li>' % (indent, value[0])
    return _helper(value, 1)

###################
# INTEGERS        #
###################

def add(value, arg):
    "Adds the arg to the value"
    return int(value) + int(arg)

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

###################
# DATES           #
###################

def date(value, arg=None):
    "Formats a date according to the given format"
    from django.utils.dateformat import format
    if not value:
        return u''
    if arg is None:
        arg = settings.DATE_FORMAT
    return format(value, arg)

def time(value, arg=None):
    "Formats a time according to the given format"
    from django.utils.dateformat import time_format
    if value in (None, u''):
        return u''
    if arg is None:
        arg = settings.TIME_FORMAT
    return time_format(value, arg)

def timesince(value, arg=None):
    'Formats a date as the time since that date (i.e. "4 days, 6 hours")'
    from django.utils.timesince import timesince
    if not value:
        return u''
    if arg:
        return timesince(arg, value)
    return timesince(value)

def timeuntil(value, arg=None):
    'Formats a date as the time until that date (i.e. "4 days, 6 hours")'
    from django.utils.timesince import timesince
    from datetime import datetime
    if not value:
        return u''
    if arg:
        return timesince(arg, value)
    return timesince(datetime.now(), value)

###################
# LOGIC           #
###################

def default(value, arg):
    "If value is unavailable, use given default"
    return value or arg

def default_if_none(value, arg):
    "If value is None, use given default"
    if value is None:
        return arg
    return value

def divisibleby(value, arg):
    "Returns true if the value is devisible by the argument"
    return int(value) % int(arg) == 0

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
    except ValueError: # unpack list of wrong size (no "maybe" value provided)
        yes, no, maybe = bits[0], bits[1], bits[1]
    if value is None:
        return maybe
    if value:
        return yes
    return no

###################
# MISC            #
###################

def filesizeformat(bytes):
    """
    Format the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB, 102
    bytes, etc).
    """
    try:
        bytes = float(bytes)
    except TypeError:
        return u"0 bytes"

    if bytes < 1024:
        return u"%d byte%s" % (bytes, bytes != 1 and u's' or u'')
    if bytes < 1024 * 1024:
        return u"%.1f KB" % (bytes / 1024)
    if bytes < 1024 * 1024 * 1024:
        return u"%.1f MB" % (bytes / (1024 * 1024))
    return u"%.1f GB" % (bytes / (1024 * 1024 * 1024))

def pluralize(value, arg=u's'):
    """
    Returns a plural suffix if the value is not 1, for '1 vote' vs. '2 votes'
    By default, 's' is used as a suffix; if an argument is provided, that string
    is used instead. If the provided argument contains a comma, the text before
    the comma is used for the singular case.
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
    except ValueError: # invalid string that's not a number
        pass
    except TypeError: # value isn't a string or a number; maybe it's a list?
        try:
            if len(value) != 1:
                return plural_suffix
        except TypeError: # len() of unsized object
            pass
    return singular_suffix

def phone2numeric(value):
    "Takes a phone number and converts it in to its numerical equivalent"
    from django.utils.text import phone2numeric
    return phone2numeric(value)

def pprint(value):
    "A wrapper around pprint.pprint -- for debugging, really"
    from pprint import pformat
    try:
        return pformat(value)
    except Exception, e:
        return u"Error in formatting:%s" % e

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
register.filter(filesizeformat)
register.filter(first)
register.filter(fix_ampersands)
register.filter(floatformat)
register.filter(get_digit)
register.filter(join)
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
