"Default variable filters"

import template, re
import random as random_module

###################
# STRINGS         #
###################

def addslashes(value, _):
    "Adds slashes - useful for passing strings to JavaScript, for example."
    return value.replace('"', '\\"').replace("'", "\\'")

def capfirst(value, _):
    "Capitalizes the first character of the value"
    value = str(value)
    return value and value[0].upper() + value[1:]

def fix_ampersands(value, _):
    "Replaces ampersands with ``&amp;`` entities"
    from django.utils.html import fix_ampersands
    return fix_ampersands(value)

def floatformat(text, _):
    """
    Displays a floating point number as 34.2 (with one decimal place) - but
    only if there's a point to be displayed
    """
    from math import modf
    if not text:
        return ''
    if modf(float(text))[0] < 0.1:
        return text
    return "%.1f" % float(text)

def linenumbers(value, _):
    "Displays text with line numbers"
    from django.utils.html import escape
    lines = value.split('\n')
    # Find the maximum width of the line count, for use with zero padding string format command
    width = str(len(str(len(lines))))
    for i, line in enumerate(lines):
        lines[i] = ("%0" + width  + "d. %s") % (i + 1, escape(line))
    return '\n'.join(lines)

def lower(value, _):
    "Converts a string into all lowercase"
    return value.lower()

def make_list(value, _):
    """
    Returns the value turned into a list. For an integer, it's a list of
    digits. For a string, it's a list of characters.
    """
    return list(str(value))

def slugify(value, _):
    "Converts to lowercase, removes non-alpha chars and converts spaces to hyphens"
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('\s+', '-', value)

def stringformat(value, arg):
    """
    Formats the variable according to the argument, a string formatting specifier.
    This specifier uses Python string formating syntax, with the exception that
    the leading "%" is dropped.

    See http://docs.python.org/lib/typesseq-strings.html for documentation
    of Python string formatting
    """
    try:
        return ("%" + arg) % value
    except (ValueError, TypeError):
        return ""

def title(value, _):
    "Converts a string into titlecase"
    return re.sub("([a-z])'([A-Z])", lambda m: m.group(0).lower(), value.title())

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
    if not isinstance(value, basestring):
        value = str(value)
    return truncate_words(value, length)

def upper(value, _):
    "Converts a string into all uppercase"
    return value.upper()

def urlencode(value, _):
    "Escapes a value for use in a URL"
    import urllib
    return urllib.quote(value)

def urlize(value, _):
    "Converts URLs in plain text into clickable links"
    from django.utils.html import urlize
    return urlize(value, nofollow=True)

def urlizetrunc(value, limit):
    """
    Converts URLs into clickable links, truncating URLs to the given character limit

    Argument: Length to truncate URLs to.
    """
    from django.utils.html import urlize
    return urlize(value, trim_url_limit=int(limit), nofollow=True)

def wordcount(value, _):
    "Returns the number of words"
    return len(value.split())

def wordwrap(value, arg):
    """
    Wraps words at specified line length

    Argument: number of words to wrap the text at.
    """
    from django.utils.text import wrap
    return wrap(value, int(arg))

def ljust(value, arg):
    """
    Left-aligns the value in a field of a given width

    Argument: field size
    """
    return str(value).ljust(int(arg))

def rjust(value, arg):
    """
    Right-aligns the value in a field of a given width

    Argument: field size
    """
    return str(value).rjust(int(arg))

def center(value, arg):
    "Centers the value in a field of a given width"
    return str(value).center(int(arg))

def cut(value, arg):
    "Removes all values of arg from the given string"
    return value.replace(arg, '')

###################
# HTML STRINGS    #
###################

def escape(value, _):
    "Escapes a string's HTML"
    from django.utils.html import escape
    return escape(value)

def linebreaks(value, _):
    "Converts newlines into <p> and <br />s"
    from django.utils.html import linebreaks
    return linebreaks(value)

def linebreaksbr(value, _):
    "Converts newlines into <br />s"
    return value.replace('\n', '<br />')

def removetags(value, tags):
    "Removes a space separated list of [X]HTML tags from the output"
    tags = [re.escape(tag) for tag in tags.split()]
    tags_re = '(%s)' % '|'.join(tags)
    starttag_re = re.compile('<%s(>|(\s+[^>]*>))' % tags_re)
    endtag_re = re.compile('</%s>' % tags_re)
    value = starttag_re.sub('', value)
    value = endtag_re.sub('', value)
    return value

def striptags(value, _):
    "Strips all [X]HTML tags"
    from django.utils.html import strip_tags
    if not isinstance(value, basestring):
        value = str(value)
    return strip_tags(value)

###################
# LISTS           #
###################

def dictsort(value, arg):
    """
    Takes a list of dicts, returns that list sorted by the property given in
    the argument.
    """
    decorated = [(template.resolve_variable('var.' + arg, {'var' : item}), item) for item in value]
    decorated.sort()
    return [item[1] for item in decorated]

def dictsortreversed(value, arg):
    """
    Takes a list of dicts, returns that list sorted in reverse order by the
    property given in the argument.
    """
    decorated = [(template.resolve_variable('var.' + arg, {'var' : item}), item) for item in value]
    decorated.sort()
    decorated.reverse()
    return [item[1] for item in decorated]

def first(value, _):
    "Returns the first item in a list"
    try:
        return value[0]
    except IndexError:
        return ''

def join(value, arg):
    "Joins a list with a string, like Python's ``str.join(list)``"
    try:
        return arg.join(map(str, value))
    except AttributeError: # fail silently but nicely
        return value

def length(value, _):
    "Returns the length of the value - useful for lists"
    return len(value)

def length_is(value, arg):
    "Returns a boolean of whether the value's length is the argument"
    return len(value) == int(arg)

def random(value, _):
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
        return value[slice(*[x and int(x) or None for x in arg.split(':')])]
    except (ValueError, TypeError):
        return value # Fail silently.

def unordered_list(value, _):
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
        indent = '\t' * tabs
        if value[1]:
            return '%s<li>%s\n%s<ul>\n%s\n%s</ul>\n%s</li>' % (indent, value[0], indent,
                '\n'.join([unordered_list(v, tabs+1) for v in value[1]]), indent, indent)
        else:
            return '%s<li>%s</li>' % (indent, value[0])
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

def date(value, arg):
    "Formats a date according to the given format"
    from django.utils.dateformat import format
    return format(value, arg)

def time(value, arg):
    "Formats a time according to the given format"
    from django.utils.dateformat import time_format
    return time_format(value, arg)

def timesince(value, _):
    'Formats a date as the time since that date (i.e. "4 days, 6 hours")'
    from django.utils.timesince import timesince
    return timesince(value)

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

def yesno(value, arg):
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
    bits = arg.split(',')
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

def filesizeformat(bytes, _):
    """
    Format the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB, 102
    bytes, etc).
    """
    bytes = float(bytes)
    if bytes < 1024:
        return "%d byte%s" % (bytes, bytes != 1 and 's' or '')
    if bytes < 1024 * 1024:
        return "%.1f KB" % (bytes / 1024)
    if bytes < 1024 * 1024 * 1024:
        return "%.1f MB" % (bytes / (1024 * 1024))
    return "%.1f GB" % (bytes / (1024 * 1024 * 1024))

def pluralize(value, _):
    "Returns 's' if the value is not 1, for '1 vote' vs. '2 votes'"
    try:
        if int(value) != 1:
            return 's'
    except ValueError: # invalid string that's not a number
        pass
    except TypeError: # value isn't a string or a number; maybe it's a list?
        try:
            if len(value) != 1:
                return 's'
        except TypeError: # len() of unsized object
            pass
    return ''

def phone2numeric(value, _):
    "Takes a phone number and converts it in to its numerical equivalent"
    from django.utils.text import phone2numeric
    return phone2numeric(value)

def pprint(value, _):
    "A wrapper around pprint.pprint -- for debugging, really"
    from pprint import pformat
    return pformat(value)

# Syntax: template.register_filter(name of filter, callback, has_argument)
template.register_filter('add', add, True)
template.register_filter('addslashes', addslashes, False)
template.register_filter('capfirst', capfirst, False)
template.register_filter('center', center, True)
template.register_filter('cut', cut, True)
template.register_filter('date', date, True)
template.register_filter('default', default, True)
template.register_filter('dictsort', dictsort, True)
template.register_filter('dictsortreversed', dictsortreversed, True)
template.register_filter('divisibleby', divisibleby, True)
template.register_filter('escape', escape, False)
template.register_filter('filesizeformat', filesizeformat, False)
template.register_filter('first', first, False)
template.register_filter('fix_ampersands', fix_ampersands, False)
template.register_filter('floatformat', floatformat, False)
template.register_filter('get_digit', get_digit, True)
template.register_filter('join', join, True)
template.register_filter('length', length, False)
template.register_filter('length_is', length_is, True)
template.register_filter('linebreaks', linebreaks, False)
template.register_filter('linebreaksbr', linebreaksbr, False)
template.register_filter('linenumbers', linenumbers, False)
template.register_filter('ljust', ljust, True)
template.register_filter('lower', lower, False)
template.register_filter('make_list', make_list, False)
template.register_filter('phone2numeric', phone2numeric, False)
template.register_filter('pluralize', pluralize, False)
template.register_filter('pprint', pprint, False)
template.register_filter('removetags', removetags, True)
template.register_filter('random', random, False)
template.register_filter('rjust', rjust, True)
template.register_filter('slice', slice_, True)
template.register_filter('slugify', slugify, False)
template.register_filter('stringformat', stringformat, True)
template.register_filter('striptags', striptags, False)
template.register_filter('time', time, True)
template.register_filter('timesince', timesince, False)
template.register_filter('title', title, False)
template.register_filter('truncatewords', truncatewords, True)
template.register_filter('unordered_list', unordered_list, False)
template.register_filter('upper', upper, False)
template.register_filter('urlencode', urlencode, False)
template.register_filter('urlize', urlize, False)
template.register_filter('urlizetrunc', urlizetrunc, True)
template.register_filter('wordcount', wordcount, False)
template.register_filter('wordwrap', wordwrap, True)
template.register_filter('yesno', yesno, True)
