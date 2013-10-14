"""Default variable filters."""
from __future__ import unicode_literals

import re
import random as random_module
from decimal import Decimal, InvalidOperation, Context, ROUND_HALF_UP
from functools import wraps
from pprint import pformat

from django.template.base import Variable, Library, VariableDoesNotExist
from django.conf import settings
from django.utils import formats
from django.utils.dateformat import format, time_format
from django.utils.encoding import force_text, iri_to_uri
from django.utils.html import (conditional_escape, escapejs, fix_ampersands,
    escape, urlize as urlize_impl, linebreaks, strip_tags, avoid_wrapping)
from django.utils.http import urlquote
from django.utils.text import Truncator, wrap, phone2numeric
from django.utils.safestring import mark_safe, SafeData, mark_for_escaping
from django.utils import six
from django.utils.timesince import timesince, timeuntil
from django.utils.translation import ugettext, ungettext
from django.utils.text import normalize_newlines

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
            args[0] = force_text(args[0])
            if (isinstance(args[0], SafeData) and
                getattr(_dec._decorated_function, 'is_safe', False)):
                return mark_safe(func(*args, **kwargs))
        return func(*args, **kwargs)

    # Include a reference to the real function (used to check original
    # arguments by the template parser, and to bear the 'is_safe' attribute
    # when multiple decorators are applied).
    _dec._decorated_function = getattr(func, '_decorated_function', func)

    return wraps(func)(_dec)


###################
# STRINGS         #
###################

@register.filter(is_safe=True)
@stringfilter
def addslashes(value):
    """
    Adds slashes before quotes. Useful for escaping strings in CSV, for
    example. Less useful for escaping JavaScript; use the ``escapejs``
    filter instead.
    """
    return value.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")

@register.filter(is_safe=True)
@stringfilter
def capfirst(value):
    """Capitalizes the first character of the value."""
    return value and value[0].upper() + value[1:]

@register.filter("escapejs")
@stringfilter
def escapejs_filter(value):
    """Hex encodes characters for use in JavaScript strings."""
    return escapejs(value)

@register.filter("fix_ampersands", is_safe=True)
@stringfilter
def fix_ampersands_filter(value):
    """Replaces ampersands with ``&amp;`` entities."""
    return fix_ampersands(value)

# Values for testing floatformat input against infinity and NaN representations,
# which differ across platforms and Python versions.  Some (i.e. old Windows
# ones) are not recognized by Decimal but we want to return them unchanged vs.
# returning an empty string as we do for completely invalid input.  Note these
# need to be built up from values that are not inf/nan, since inf/nan values do
# not reload properly from .pyc files on Windows prior to some level of Python 2.5
# (see Python Issue757815 and Issue1080440).
pos_inf = 1e200 * 1e200
neg_inf = -1e200 * 1e200
nan = (1e200 * 1e200) // (1e200 * 1e200)
special_floats = [str(pos_inf), str(neg_inf), str(nan)]

@register.filter(is_safe=True)
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
        input_val = force_text(text)
        d = Decimal(input_val)
    except UnicodeEncodeError:
        return ''
    except InvalidOperation:
        if input_val in special_floats:
            return input_val
        try:
            d = Decimal(force_text(float(text)))
        except (ValueError, InvalidOperation, TypeError, UnicodeEncodeError):
            return ''
    try:
        p = int(arg)
    except ValueError:
        return input_val

    try:
        m = int(d) - d
    except (ValueError, OverflowError, InvalidOperation):
        return input_val

    if not m and p < 0:
        return mark_safe(formats.number_format('%d' % (int(d)), 0))

    if p == 0:
        exp = Decimal(1)
    else:
        exp = Decimal('1.0') / (Decimal(10) ** abs(p))
    try:
        # Set the precision high enough to avoid an exception, see #15789.
        tupl = d.as_tuple()
        units = len(tupl[1]) - tupl[2]
        prec = abs(p) + units + 1

        # Avoid conversion to scientific notation by accessing `sign`, `digits`
        # and `exponent` from `Decimal.as_tuple()` directly.
        sign, digits, exponent = d.quantize(exp, ROUND_HALF_UP,
            Context(prec=prec)).as_tuple()
        digits = [six.text_type(digit) for digit in reversed(digits)]
        while len(digits) <= abs(exponent):
            digits.append('0')
        digits.insert(-exponent, '.')
        if sign:
            digits.append('-')
        number = ''.join(reversed(digits))
        return mark_safe(formats.number_format(number, abs(p)))
    except InvalidOperation:
        return input_val

@register.filter(is_safe=True)
@stringfilter
def iriencode(value):
    """Escapes an IRI value for use in a URL."""
    return force_text(iri_to_uri(value))

@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def linenumbers(value, autoescape=None):
    """Displays text with line numbers."""
    lines = value.split('\n')
    # Find the maximum width of the line count, for use with zero padding
    # string format command
    width = six.text_type(len(six.text_type(len(lines))))
    if not autoescape or isinstance(value, SafeData):
        for i, line in enumerate(lines):
            lines[i] = ("%0" + width  + "d. %s") % (i + 1, line)
    else:
        for i, line in enumerate(lines):
            lines[i] = ("%0" + width  + "d. %s") % (i + 1, escape(line))
    return mark_safe('\n'.join(lines))

@register.filter(is_safe=True)
@stringfilter
def lower(value):
    """Converts a string into all lowercase."""
    return value.lower()

@register.filter(is_safe=False)
@stringfilter
def make_list(value):
    """
    Returns the value turned into a list.

    For an integer, it's a list of digits.
    For a string, it's a list of characters.
    """
    return list(value)

@register.filter(is_safe=True)
@stringfilter
def slugify(value):
    """
    Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.
    """
    from django.utils.text import slugify
    return slugify(value)

@register.filter(is_safe=True)
def stringformat(value, arg):
    """
    Formats the variable according to the arg, a string formatting specifier.

    This specifier uses Python string formating syntax, with the exception that
    the leading "%" is dropped.

    See http://docs.python.org/lib/typesseq-strings.html for documentation
    of Python string formatting
    """
    try:
        return ("%" + six.text_type(arg)) % value
    except (ValueError, TypeError):
        return ""

@register.filter(is_safe=True)
@stringfilter
def title(value):
    """Converts a string into titlecase."""
    t = re.sub("([a-z])'([A-Z])", lambda m: m.group(0).lower(), value.title())
    return re.sub("\d([A-Z])", lambda m: m.group(0).lower(), t)

@register.filter(is_safe=True)
@stringfilter
def truncatechars(value, arg):
    """
    Truncates a string after a certain number of characters.

    Argument: Number of characters to truncate after.
    """
    try:
        length = int(arg)
    except ValueError: # Invalid literal for int().
        return value # Fail silently.
    return Truncator(value).chars(length)

@register.filter(is_safe=True)
@stringfilter
def truncatewords(value, arg):
    """
    Truncates a string after a certain number of words.

    Argument: Number of words to truncate after.

    Newlines within the string are removed.
    """
    try:
        length = int(arg)
    except ValueError: # Invalid literal for int().
        return value # Fail silently.
    return Truncator(value).words(length, truncate=' ...')

@register.filter(is_safe=True)
@stringfilter
def truncatewords_html(value, arg):
    """
    Truncates HTML after a certain number of words.

    Argument: Number of words to truncate after.

    Newlines in the HTML are preserved.
    """
    try:
        length = int(arg)
    except ValueError: # invalid literal for int()
        return value # Fail silently.
    return Truncator(value).words(length, html=True, truncate=' ...')

@register.filter(is_safe=False)
@stringfilter
def upper(value):
    """Converts a string into all uppercase."""
    return value.upper()

@register.filter(is_safe=False)
@stringfilter
def urlencode(value, safe=None):
    """
    Escapes a value for use in a URL.

    Takes an optional ``safe`` parameter used to determine the characters which
    should not be escaped by Django's ``urlquote`` method. If not provided, the
    default safe characters will be used (but an empty string can be provided
    when *all* characters should be escaped).
    """
    kwargs = {}
    if safe is not None:
        kwargs['safe'] = safe
    return urlquote(value, **kwargs)

@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def urlize(value, autoescape=None):
    """Converts URLs in plain text into clickable links."""
    return mark_safe(urlize_impl(value, nofollow=True, autoescape=autoescape))

@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def urlizetrunc(value, limit, autoescape=None):
    """
    Converts URLs into clickable links, truncating URLs to the given character
    limit, and adding 'rel=nofollow' attribute to discourage spamming.

    Argument: Length to truncate URLs to.
    """
    return mark_safe(urlize_impl(value, trim_url_limit=int(limit), nofollow=True,
                            autoescape=autoescape))

@register.filter(is_safe=False)
@stringfilter
def wordcount(value):
    """Returns the number of words."""
    return len(value.split())

@register.filter(is_safe=True)
@stringfilter
def wordwrap(value, arg):
    """
    Wraps words at specified line length.

    Argument: number of characters to wrap the text at.
    """
    return wrap(value, int(arg))

@register.filter(is_safe=True)
@stringfilter
def ljust(value, arg):
    """
    Left-aligns the value in a field of a given width.

    Argument: field size.
    """
    return value.ljust(int(arg))

@register.filter(is_safe=True)
@stringfilter
def rjust(value, arg):
    """
    Right-aligns the value in a field of a given width.

    Argument: field size.
    """
    return value.rjust(int(arg))

@register.filter(is_safe=True)
@stringfilter
def center(value, arg):
    """Centers the value in a field of a given width."""
    return value.center(int(arg))

@register.filter
@stringfilter
def cut(value, arg):
    """
    Removes all values of arg from the given string.
    """
    safe = isinstance(value, SafeData)
    value = value.replace(arg, '')
    if safe and arg != ';':
        return mark_safe(value)
    return value

###################
# HTML STRINGS    #
###################

@register.filter("escape", is_safe=True)
@stringfilter
def escape_filter(value):
    """
    Marks the value as a string that should not be auto-escaped.
    """
    return mark_for_escaping(value)

@register.filter(is_safe=True)
@stringfilter
def force_escape(value):
    """
    Escapes a string's HTML. This returns a new string containing the escaped
    characters (as opposed to "escape", which marks the content for later
    possible escaping).
    """
    return escape(value)

@register.filter("linebreaks", is_safe=True, needs_autoescape=True)
@stringfilter
def linebreaks_filter(value, autoescape=None):
    """
    Replaces line breaks in plain text with appropriate HTML; a single
    newline becomes an HTML line break (``<br />``) and a new line
    followed by a blank line becomes a paragraph break (``</p>``).
    """
    autoescape = autoescape and not isinstance(value, SafeData)
    return mark_safe(linebreaks(value, autoescape))

@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def linebreaksbr(value, autoescape=None):
    """
    Converts all newlines in a piece of plain text to HTML line breaks
    (``<br />``).
    """
    autoescape = autoescape and not isinstance(value, SafeData)
    value = normalize_newlines(value)
    if autoescape:
        value = escape(value)
    return mark_safe(value.replace('\n', '<br />'))

@register.filter(is_safe=True)
@stringfilter
def safe(value):
    """
    Marks the value as a string that should not be auto-escaped.
    """
    return mark_safe(value)

@register.filter(is_safe=True)
def safeseq(value):
    """
    A "safe" filter for sequences. Marks each element in the sequence,
    individually, as safe, after converting them to unicode. Returns a list
    with the results.
    """
    return [mark_safe(force_text(obj)) for obj in value]

@register.filter(is_safe=True)
@stringfilter
def removetags(value, tags):
    """Removes a space separated list of [X]HTML tags from the output."""
    from django.utils.html import remove_tags
    return remove_tags(value, tags)

@register.filter(is_safe=True)
@stringfilter
def striptags(value):
    """Strips all [X]HTML tags."""
    return strip_tags(value)

###################
# LISTS           #
###################

@register.filter(is_safe=False)
def dictsort(value, arg):
    """
    Takes a list of dicts, returns that list sorted by the property given in
    the argument.
    """
    try:
        return sorted(value, key=Variable(arg).resolve)
    except (TypeError, VariableDoesNotExist):
        return ''

@register.filter(is_safe=False)
def dictsortreversed(value, arg):
    """
    Takes a list of dicts, returns that list sorted in reverse order by the
    property given in the argument.
    """
    try:
        return sorted(value, key=Variable(arg).resolve, reverse=True)
    except (TypeError, VariableDoesNotExist):
        return ''

@register.filter(is_safe=False)
def first(value):
    """Returns the first item in a list."""
    try:
        return value[0]
    except IndexError:
        return ''

@register.filter(is_safe=True, needs_autoescape=True)
def join(value, arg, autoescape=None):
    """
    Joins a list with a string, like Python's ``str.join(list)``.
    """
    value = map(force_text, value)
    if autoescape:
        value = [conditional_escape(v) for v in value]
    try:
        data = conditional_escape(arg).join(value)
    except AttributeError: # fail silently but nicely
        return value
    return mark_safe(data)

@register.filter(is_safe=True)
def last(value):
    "Returns the last item in a list"
    try:
        return value[-1]
    except IndexError:
        return ''

@register.filter(is_safe=True)
def length(value):
    """Returns the length of the value - useful for lists."""
    try:
        return len(value)
    except (ValueError, TypeError):
        return ''

@register.filter(is_safe=False)
def length_is(value, arg):
    """Returns a boolean of whether the value's length is the argument."""
    try:
        return len(value) == int(arg)
    except (ValueError, TypeError):
        return ''

@register.filter(is_safe=True)
def random(value):
    """Returns a random item from the list."""
    return random_module.choice(value)

@register.filter("slice", is_safe=True)
def slice_filter(value, arg):
    """
    Returns a slice of the list.

    Uses the same syntax as Python's list slicing; see
    http://www.diveintopython3.net/native-datatypes.html#slicinglists
    for an introduction.
    """
    try:
        bits = []
        for x in arg.split(':'):
            if len(x) == 0:
                bits.append(None)
            else:
                bits.append(int(x))
        return value[slice(*bits)]

    except (ValueError, TypeError):
        return value # Fail silently.

@register.filter(is_safe=True, needs_autoescape=True)
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
        try:
            # see if second item is iterable
            iter(second_item)
        except TypeError:
            return list_, False
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
        indent = '\t' * tabs
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
                    escaper(force_text(title)), sublist))
            i += 1
        return '\n'.join(output)
    value, converted = convert_old_style_list(value)
    return mark_safe(_helper(value))

###################
# INTEGERS        #
###################

@register.filter(is_safe=False)
def add(value, arg):
    """Adds the arg to the value."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except Exception:
            return ''

@register.filter(is_safe=False)
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

@register.filter(expects_localtime=True, is_safe=False)
def date(value, arg=None):
    """Formats a date according to the given format."""
    if value in (None, ''):
        return ''
    if arg is None:
        arg = settings.DATE_FORMAT
    try:
        return formats.date_format(value, arg)
    except AttributeError:
        try:
            return format(value, arg)
        except AttributeError:
            return ''

@register.filter(expects_localtime=True, is_safe=False)
def time(value, arg=None):
    """Formats a time according to the given format."""
    if value in (None, ''):
        return ''
    if arg is None:
        arg = settings.TIME_FORMAT
    try:
        return formats.time_format(value, arg)
    except AttributeError:
        try:
            return time_format(value, arg)
        except AttributeError:
            return ''

@register.filter("timesince", is_safe=False)
def timesince_filter(value, arg=None):
    """Formats a date as the time since that date (i.e. "4 days, 6 hours")."""
    if not value:
        return ''
    try:
        if arg:
            return timesince(value, arg)
        return timesince(value)
    except (ValueError, TypeError):
        return ''

@register.filter("timeuntil", is_safe=False)
def timeuntil_filter(value, arg=None):
    """Formats a date as the time until that date (i.e. "4 days, 6 hours")."""
    if not value:
        return ''
    try:
        return timeuntil(value, arg)
    except (ValueError, TypeError):
        return ''

###################
# LOGIC           #
###################

@register.filter(is_safe=False)
def default(value, arg):
    """If value is unavailable, use given default."""
    return value or arg

@register.filter(is_safe=False)
def default_if_none(value, arg):
    """If value is None, use given default."""
    if value is None:
        return arg
    return value

@register.filter(is_safe=False)
def divisibleby(value, arg):
    """Returns True if the value is devisible by the argument."""
    return int(value) % int(arg) == 0

@register.filter(is_safe=False)
def yesno(value, arg=None):
    """
    Given a string mapping values for true, false and (optionally) None,
    returns one of those strings according to the value:

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
    bits = arg.split(',')
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

###################
# MISC            #
###################

@register.filter(is_safe=True)
def filesizeformat(bytes):
    """
    Formats the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
    102 bytes, etc).
    """
    try:
        bytes = float(bytes)
    except (TypeError,ValueError,UnicodeDecodeError):
        value = ungettext("%(size)d byte", "%(size)d bytes", 0) % {'size': 0}
        return avoid_wrapping(value)

    filesize_number_format = lambda value: formats.number_format(round(value, 1), 1)

    KB = 1<<10
    MB = 1<<20
    GB = 1<<30
    TB = 1<<40
    PB = 1<<50

    if bytes < KB:
        value = ungettext("%(size)d byte", "%(size)d bytes", bytes) % {'size': bytes}
    elif bytes < MB:
        value = ugettext("%s KB") % filesize_number_format(bytes / KB)
    elif bytes < GB:
        value = ugettext("%s MB") % filesize_number_format(bytes / MB)
    elif bytes < TB:
        value = ugettext("%s GB") % filesize_number_format(bytes / GB)
    elif bytes < PB:
        value = ugettext("%s TB") % filesize_number_format(bytes / TB)
    else:
        value = ugettext("%s PB") % filesize_number_format(bytes / PB)

    return avoid_wrapping(value)

@register.filter(is_safe=False)
def pluralize(value, arg='s'):
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
    if not ',' in arg:
        arg = ',' + arg
    bits = arg.split(',')
    if len(bits) > 2:
        return ''
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

@register.filter("phone2numeric", is_safe=True)
def phone2numeric_filter(value):
    """Takes a phone number and converts it in to its numerical equivalent."""
    return phone2numeric(value)

@register.filter(is_safe=True)
def pprint(value):
    """A wrapper around pprint.pprint -- for debugging, really."""
    try:
        return pformat(value)
    except Exception as e:
        return "Error in formatting: %s" % force_text(e, errors="replace")
