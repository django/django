"""
Django validation and HTML form handling.

TODO:
    Validation not tied to a particular field
    <select> and validation of lists
    Default value for field
    Field labels
    Nestable Forms
    FatalValidationError -- short-circuits all other validators on a form
    ValidationWarning
    "This form field requires foo.js" and form.js_includes()

# Form ########################################################################

>>> class Person(Form):
...     first_name = CharField()
...     last_name = CharField()
...     birthday = DateField()
>>> p = Person({'first_name': u'John', 'last_name': u'Lennon', 'birthday': u'1940-10-9'})
>>> p.errors()
{}
>>> p.is_valid()
True
>>> p.errors().as_ul()
u''
>>> p.errors().as_text()
u''
>>> p.to_python()
{'first_name': u'John', 'last_name': u'Lennon', 'birthday': datetime.date(1940, 10, 9)}
>>> print p['first_name']
<input type="text" name="first_name" value="John" />
>>> print p['last_name']
<input type="text" name="last_name" value="Lennon" />
>>> print p['birthday']
<input type="text" name="birthday" value="1940-10-09" />
>>> for boundfield in p:
...     print boundfield
<input type="text" name="first_name" value="John" />
<input type="text" name="last_name" value="Lennon" />
<input type="text" name="birthday" value="1940-10-09" />

>>> p = Person({'last_name': u'Lennon'})
>>> p.errors()
{'first_name': [u'This field is required.'], 'birthday': [u'This field is required.']}
>>> p.is_valid()
False
>>> p.errors().as_ul()
u'<ul class="errorlist"><li>first_name<ul class="errorlist"><li>This field is required.</li></ul></li><li>birthday<ul class="errorlist"><li>This field is required.</li></ul></li></ul>'
>>> print p.errors().as_text()
* first_name
  * This field is required.
* birthday
  * This field is required.
>>> p.to_python()
>>> repr(p.to_python())
'None'
>>> p['first_name'].errors
[u'This field is required.']
>>> p['first_name'].errors.as_ul()
u'<ul class="errorlist"><li>This field is required.</li></ul>'
>>> p['first_name'].errors.as_text()
u'* This field is required.'

>>> p = Person()
>>> print p['first_name']
<input type="text" name="first_name" />
>>> print p['last_name']
<input type="text" name="last_name" />
>>> print p['birthday']
<input type="text" name="birthday" />

>>> class SignupForm(Form):
...     email = EmailField()
...     get_spam = BooleanField()
>>> f = SignupForm()
>>> print f['email']
<input type="text" name="email" />
>>> print f['get_spam']
<input type="checkbox" name="get_spam" />

>>> f = SignupForm({'email': 'test@example.com', 'get_spam': True})
>>> print f['email']
<input type="text" name="email" value="test@example.com" />
>>> print f['get_spam']
<input checked="checked" type="checkbox" name="get_spam" />

Any Field can have a Widget class passed to its constructor:
>>> class ContactForm(Form):
...     subject = CharField()
...     message = CharField(widget=Textarea)
>>> f = ContactForm()
>>> print f['subject']
<input type="text" name="subject" />
>>> print f['message']
<textarea name="message"></textarea>

as_textarea() and as_text() are shortcuts for changing the output widget type:
>>> f['subject'].as_textarea()
u'<textarea name="subject"></textarea>'
>>> f['message'].as_text()
u'<input type="text" name="message" />'

The 'widget' parameter to a Field can also be an instance:
>>> class ContactForm(Form):
...     subject = CharField()
...     message = CharField(widget=Textarea(attrs={'rows': 80, 'cols': 20}))
>>> f = ContactForm()
>>> print f['message']
<textarea rows="80" cols="20" name="message"></textarea>

Instance-level attrs are *not* carried over to as_textarea() and as_text():
>>> f['message'].as_text()
u'<input type="text" name="message" />'
>>> f = ContactForm({'subject': 'Hello', 'message': 'I love you.'})
>>> f['subject'].as_textarea()
u'<textarea name="subject">Hello</textarea>'
>>> f['message'].as_text()
u'<input type="text" name="message" value="I love you." />'
"""

from django.utils.html import escape
import datetime
import re
import time

# Default encoding for input byte strings.
DEFAULT_ENCODING = 'utf-8' # TODO: First look at django.conf.settings, then fall back to this.

def smart_unicode(s):
    if not isinstance(s, unicode):
        s = unicode(s, DEFAULT_ENCODING)
    return s

###################
# VALIDATOR STUFF #
###################

class ErrorDict(dict):
    """
    A collection of errors that knows how to display itself in various formats.

    The dictionary keys are the field names, and the values are the errors.
    """
    def __str__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return u''
        return u'<ul class="errorlist">%s</ul>' % ''.join([u'<li>%s%s</li>' % (k, v) for k, v in self.items()])

    def as_text(self):
        return u'\n'.join([u'* %s\n%s' % (k, u'\n'.join([u'  * %s' % i for i in v])) for k, v in self.items()])

class ErrorList(list):
    """
    A collection of errors that knows how to display itself in various formats.
    """
    def __str__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return u''
        return u'<ul class="errorlist">%s</ul>' % ''.join([u'<li>%s</li>' % e for e in self])

    def as_text(self):
        if not self: return u''
        return u'\n'.join([u'* %s' % e for e in self])

class ValidationError(Exception):
    def __init__(self, message):
        "ValidationError can be passed a string or a list."
        if isinstance(message, list):
            self.messages = ErrorList([smart_unicode(msg) for msg in message])
        else:
            assert isinstance(message, basestring), ("%s should be a basestring" % repr(message))
            message = smart_unicode(message)
            self.messages = ErrorList([message])

    def __str__(self):
        # This is needed because, without a __str__(), printing an exception
        # instance would result in this:
        # AttributeError: ValidationError instance has no attribute 'args'
        # See http://www.python.org/doc/current/tut/node10.html#handling
        return repr(self.messages)

################
# HTML WIDGETS #
################

# Converts a dictionary to a single string with key="value", XML-style.
# Assumes keys do not need to be XML-escaped.
flatatt = lambda attrs: ' '.join(['%s="%s"' % (k, escape(v)) for k, v in attrs.items()])

class Widget(object):
    def __init__(self, attrs=None):
        self.attrs = attrs or {}

    def render(self, name, value):
        raise NotImplementedError

class TextInput(Widget):
    """
    >>> w = TextInput()
    >>> w.render('email', '')
    u'<input type="text" name="email" />'
    >>> w.render('email', None)
    u'<input type="text" name="email" />'
    >>> w.render('email', 'test@example.com')
    u'<input type="text" name="email" value="test@example.com" />'
    >>> w.render('email', 'some "quoted" & ampersanded value')
    u'<input type="text" name="email" value="some &quot;quoted&quot; &amp; ampersanded value" />'
    >>> w.render('email', 'test@example.com', attrs={'class': 'fun'})
    u'<input type="text" name="email" value="test@example.com" class="fun" />'

    You can also pass 'attrs' to the constructor:
    >>> w = TextInput(attrs={'class': 'fun'})
    >>> w.render('email', '')
    u'<input type="text" class="fun" name="email" />'
    >>> w.render('email', 'foo@example.com')
    u'<input type="text" class="fun" value="foo@example.com" name="email" />'

    'attrs' passed to render() get precedence over those passed to the constructor:
    >>> w = TextInput(attrs={'class': 'pretty'})
    >>> w.render('email', '', attrs={'class': 'special'})
    u'<input type="text" class="special" name="email" />'
    """
    def render(self, name, value, attrs=None):
        if value in EMPTY_VALUES: value = ''
        final_attrs = dict(self.attrs, type='text', name=name)
        if attrs:
            final_attrs.update(attrs)
        if value != '': final_attrs['value'] = value # Only add the 'value' attribute if a value is non-empty.
        return u'<input %s />' % flatatt(final_attrs)

class Textarea(Widget):
    """
    >>> w = Textarea()
    >>> w.render('msg', '')
    u'<textarea name="msg"></textarea>'
    >>> w.render('msg', None)
    u'<textarea name="msg"></textarea>'
    >>> w.render('msg', 'value')
    u'<textarea name="msg">value</textarea>'
    >>> w.render('msg', 'some "quoted" & ampersanded value')
    u'<textarea name="msg">some &quot;quoted&quot; &amp; ampersanded value</textarea>'
    >>> w.render('msg', 'value', attrs={'class': 'pretty'})
    u'<textarea name="msg" class="pretty">value</textarea>'

    You can also pass 'attrs' to the constructor:
    >>> w = Textarea(attrs={'class': 'pretty'})
    >>> w.render('msg', '')
    u'<textarea class="pretty" name="msg"></textarea>'
    >>> w.render('msg', 'example')
    u'<textarea class="pretty" name="msg">example</textarea>'

    'attrs' passed to render() get precedence over those passed to the constructor:
    >>> w = Textarea(attrs={'class': 'pretty'})
    >>> w.render('msg', '', attrs={'class': 'special'})
    u'<textarea class="special" name="msg"></textarea>'
    """
    def render(self, name, value, attrs=None):
        if value in EMPTY_VALUES: value = ''
        final_attrs = dict(self.attrs, name=name)
        if attrs:
            final_attrs.update(attrs)
        return u'<textarea %s>%s</textarea>' % (flatatt(final_attrs), escape(value))

class CheckboxInput(Widget):
    """
    >>> w = CheckboxInput()
    >>> w.render('is_cool', '')
    u'<input type="checkbox" name="is_cool" />'
    >>> w.render('is_cool', False)
    u'<input type="checkbox" name="is_cool" />'
    >>> w.render('is_cool', True)
    u'<input checked="checked" type="checkbox" name="is_cool" />'
    >>> w.render('is_cool', False, attrs={'class': 'pretty'})
    u'<input type="checkbox" name="is_cool" class="pretty" />'

    You can also pass 'attrs' to the constructor:
    >>> w = CheckboxInput(attrs={'class': 'pretty'})
    >>> w.render('is_cool', '')
    u'<input type="checkbox" class="pretty" name="is_cool" />'

    'attrs' passed to render() get precedence over those passed to the constructor:
    >>> w = CheckboxInput(attrs={'class': 'pretty'})
    >>> w.render('is_cool', '', attrs={'class': 'special'})
    u'<input type="checkbox" class="special" name="is_cool" />'
    """
    def render(self, name, value, attrs=None):
        final_attrs = dict(self.attrs, type='checkbox', name=name)
        if attrs:
            final_attrs.update(attrs)
        if value: final_attrs['checked'] = 'checked'
        return u'<input %s />' % flatatt(final_attrs)

##########
# FIELDS #
##########

# These values, if given to to_python(), will trigger the self.required check.
EMPTY_VALUES = (None, '')

class Field(object):
    widget = TextInput # Default widget to use when rendering this type of Field.

    def __init__(self, required=True, widget=None):
        self.required = required
        widget = widget or self.widget
        if isinstance(widget, type):
            widget = widget()
        self.widget = widget

    def to_python(self, value):
        """
        Validates the given value and returns its "normalized" value as an
        appropriate Python object.

        Raises ValidationError for any errors.
        """
        if self.required and value in EMPTY_VALUES:
            raise ValidationError(u'This field is required.')
        return value

class CharField(Field):
    """
    >>> f = CharField(required=False)
    >>> f.to_python(1)
    u'1'
    >>> f.to_python('hello')
    u'hello'
    >>> f.to_python(None)
    u''
    >>> f.to_python([1, 2, 3])
    u'[1, 2, 3]'

    CharField accepts an optional max_length parameter:
    >>> f = CharField(max_length=10, required=False)
    >>> f.to_python('')
    u''
    >>> f.to_python('12345')
    u'12345'
    >>> f.to_python('1234567890')
    u'1234567890'
    >>> f.to_python('1234567890a')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Ensure this value has at most 10 characters.']

    CharField accepts an optional min_length parameter:
    >>> f = CharField(min_length=10, required=False)
    >>> f.to_python('')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Ensure this value has at least 10 characters.']
    >>> f.to_python('12345')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Ensure this value has at least 10 characters.']
    >>> f.to_python('1234567890')
    u'1234567890'
    >>> f.to_python('1234567890a')
    u'1234567890a'
    """
    def __init__(self, max_length=None, min_length=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.max_length, self.min_length = max_length, min_length

    def to_python(self, value):
        "Validates max_length and min_length. Returns a Unicode object."
        Field.to_python(self, value)
        if value in EMPTY_VALUES: value = u''
        if not isinstance(value, basestring):
            value = unicode(str(value), DEFAULT_ENCODING)
        elif not isinstance(value, unicode):
            value = unicode(value, DEFAULT_ENCODING)
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(u'Ensure this value has at most %d characters.' % self.max_length)
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(u'Ensure this value has at least %d characters.' % self.min_length)
        return value

class IntegerField(Field):
    """
    >>> f = IntegerField()
    >>> f.to_python('1')
    1
    >>> isinstance(f.to_python('1'), int)
    True
    >>> f.to_python('23')
    23
    >>> f.to_python('a')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a whole number.']
    >>> f.to_python('1 ')
    1
    >>> f.to_python(' 1')
    1
    >>> f.to_python(' 1 ')
    1
    >>> f.to_python('1a')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a whole number.']
    """
    def to_python(self, value):
        """
        Validates that int() can be called on the input. Returns the result
        of int().
        """
        super(IntegerField, self).to_python(value)
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValidationError(u'Enter a whole number.')

DEFAULT_DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)

class DateField(Field):
    """
    >>> import datetime
    >>> f = DateField()
    >>> f.to_python(datetime.date(2006, 10, 25))
    datetime.date(2006, 10, 25)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
    datetime.date(2006, 10, 25)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59))
    datetime.date(2006, 10, 25)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
    datetime.date(2006, 10, 25)
    >>> f.to_python('2006-10-25')
    datetime.date(2006, 10, 25)
    >>> f.to_python('10/25/2006')
    datetime.date(2006, 10, 25)
    >>> f.to_python('10/25/06')
    datetime.date(2006, 10, 25)
    >>> f.to_python('Oct 25 2006')
    datetime.date(2006, 10, 25)
    >>> f.to_python('October 25 2006')
    datetime.date(2006, 10, 25)
    >>> f.to_python('October 25, 2006')
    datetime.date(2006, 10, 25)
    >>> f.to_python('25 October 2006')
    datetime.date(2006, 10, 25)
    >>> f.to_python('25 October, 2006')
    datetime.date(2006, 10, 25)
    >>> f.to_python('2006-4-31')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date.']
    >>> f.to_python('200a-10-25')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date.']
    >>> f.to_python('25/10/06')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date.']
    >>> f.to_python(None)
    Traceback (most recent call last):
    ...
    ValidationError: [u'This field is required.']

    >>> f = DateField(required=False)
    >>> f.to_python(None)
    >>> repr(f.to_python(None))
    'None'
    >>> f.to_python('')
    >>> repr(f.to_python(''))
    'None'

    DateField accepts an optional input_formats parameter:
    >>> f = DateField(input_formats=['%Y %m %d'])
    >>> f.to_python(datetime.date(2006, 10, 25))
    datetime.date(2006, 10, 25)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
    datetime.date(2006, 10, 25)
    >>> f.to_python('2006 10 25')
    datetime.date(2006, 10, 25)

    The input_formats parameter overrides all default input formats,
    so the default formats won't work unless you specify them:
    >>> f.to_python('2006-10-25')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date.']
    >>> f.to_python('10/25/2006')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date.']
    >>> f.to_python('10/25/06')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date.']
    """
    def __init__(self, input_formats=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.input_formats = input_formats or DEFAULT_DATE_INPUT_FORMATS

    def to_python(self, value):
        """
        Validates that the input can be converted to a date. Returns a Python
        datetime.date object.
        """
        Field.to_python(self, value)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        for format in self.input_formats:
            try:
                return datetime.date(*time.strptime(value, format)[:3])
            except ValueError:
                continue
        raise ValidationError(u'Enter a valid date.')

DEFAULT_DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)

class DateTimeField(Field):
    """
    >>> import datetime
    >>> f = DateTimeField()
    >>> f.to_python(datetime.date(2006, 10, 25))
    datetime.datetime(2006, 10, 25, 0, 0)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59))
    datetime.datetime(2006, 10, 25, 14, 30, 59)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
    datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
    >>> f.to_python('2006-10-25 14:30:45')
    datetime.datetime(2006, 10, 25, 14, 30, 45)
    >>> f.to_python('2006-10-25 14:30:00')
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python('2006-10-25 14:30')
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python('2006-10-25')
    datetime.datetime(2006, 10, 25, 0, 0)
    >>> f.to_python('10/25/2006 14:30:45')
    datetime.datetime(2006, 10, 25, 14, 30, 45)
    >>> f.to_python('10/25/2006 14:30:00')
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python('10/25/2006 14:30')
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python('10/25/2006')
    datetime.datetime(2006, 10, 25, 0, 0)
    >>> f.to_python('10/25/06 14:30:45')
    datetime.datetime(2006, 10, 25, 14, 30, 45)
    >>> f.to_python('10/25/06 14:30:00')
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python('10/25/06 14:30')
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python('10/25/06')
    datetime.datetime(2006, 10, 25, 0, 0)
    >>> f.to_python('hello')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date/time.']
    >>> f.to_python('2006-10-25 4:30 p.m.')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date/time.']

    DateField accepts an optional input_formats parameter:
    >>> f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
    >>> f.to_python(datetime.date(2006, 10, 25))
    datetime.datetime(2006, 10, 25, 0, 0)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30))
    datetime.datetime(2006, 10, 25, 14, 30)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59))
    datetime.datetime(2006, 10, 25, 14, 30, 59)
    >>> f.to_python(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
    datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
    >>> f.to_python('2006 10 25 2:30 PM')
    datetime.datetime(2006, 10, 25, 14, 30)

    The input_formats parameter overrides all default input formats,
    so the default formats won't work unless you specify them:
    >>> f.to_python('2006-10-25 14:30:45')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid date/time.']
    """
    def __init__(self, input_formats=None, required=True, widget=None):
        Field.__init__(self, required, widget)
        self.input_formats = input_formats or DEFAULT_DATETIME_INPUT_FORMATS

    def to_python(self, value):
        """
        Validates that the input can be converted to a datetime. Returns a
        Python datetime.datetime object.
        """
        Field.to_python(self, value)
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        for format in self.input_formats:
            try:
                return datetime.datetime(*time.strptime(value, format)[:6])
            except ValueError:
                continue
        raise ValidationError(u'Enter a valid date/time.')

class RegexField(Field):
    """
    >>> import re

    >>> f = RegexField('^\d[A-F]\d$')
    >>> f.to_python('2A2')
    u'2A2'
    >>> f.to_python('3F3')
    u'3F3'
    >>> f.to_python('3G3')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid value.']
    >>> f.to_python(' 2A2')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid value.']
    >>> f.to_python('2A2 ')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid value.']

    Alternatively, RegexField can take a compiled regular expression:
    >>> f = RegexField(re.compile('^\d[A-F]\d$'))
    >>> f.to_python('2A2')
    u'2A2'
    >>> f.to_python('3F3')
    u'3F3'
    >>> f.to_python('3G3')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid value.']
    >>> f.to_python(' 2A2')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid value.']
    >>> f.to_python('2A2 ')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid value.']

    RegexField takes an optional error_message argument:
    >>> f = RegexField('^\d\d\d\d$', 'Enter a four-digit number.')
    >>> f.to_python('1234')
    u'1234'
    >>> f.to_python('123')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a four-digit number.']
    >>> f.to_python('abcd')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a four-digit number.']
    """
    def __init__(self, regex, error_message=None, required=True, widget=None):
        """
        regex can be either a string or a compiled regular expression object.
        error_message is an optional error message to use, if
        'Enter a valid value' is too generic for you.
        """
        Field.__init__(self, required, widget)
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        self.regex = regex
        self.error_message = error_message or u'Enter a valid value.'

    def to_python(self, value):
        """
        Validates that the input matches the regular expression. Returns a
        Unicode object.
        """
        Field.to_python(self, value)
        if value in EMPTY_VALUES: value = u''
        if not isinstance(value, basestring):
            value = unicode(str(value), DEFAULT_ENCODING)
        elif not isinstance(value, unicode):
            value = unicode(value, DEFAULT_ENCODING)
        if not self.regex.search(value):
            raise ValidationError(self.error_message)
        return value

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain

class EmailField(RegexField):
    """
    >>> f = EmailField()
    >>> f.to_python('person@example.com')
    u'person@example.com'
    >>> f.to_python('foo')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid e-mail address.']
    >>> f.to_python('foo@')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid e-mail address.']
    >>> f.to_python('foo@bar')
    Traceback (most recent call last):
    ...
    ValidationError: [u'Enter a valid e-mail address.']
    """
    def __init__(self, required=True, widget=None):
        RegexField.__init__(self, email_re, u'Enter a valid e-mail address.', required, widget)

class BooleanField(Field):
    """
    >>> f = BooleanField()
    >>> f.to_python(True)
    True
    >>> f.to_python(False)
    False
    >>> f.to_python(1)
    True
    >>> f.to_python(0)
    False
    >>> f.to_python('Django rocks')
    True
    """
    widget = CheckboxInput

    def to_python(self, value):
        "Returns a Python boolean object."
        Field.to_python(self, value)
        return bool(value)

#########
# FORMS #
#########

class DeclarativeFieldsMetaclass(type):
    "Metaclass that converts Field attributes to a dictionary called 'fields'."
    def __new__(cls, name, bases, attrs):
        attrs['fields'] = dict([(name, attrs.pop(name)) for name, obj in attrs.items() if isinstance(obj, Field)])
        return type.__new__(cls, name, bases, attrs)

class Form(object):
    "A collection of Fields, plus their associated data."
    __metaclass__ = DeclarativeFieldsMetaclass

    def __init__(self, data=None): # TODO: prefix stuff
        self.data = data or {}
        self.__data_python = None # Stores the data after to_python() has been called.
        self.__errors = None # Stores the errors after to_python() has been called.

    def __iter__(self):
        for name, field in self.fields.items():
            yield BoundField(self, field, name)

    def to_python(self):
        if self.__errors is None:
            self._validate()
        return self.__data_python

    def errors(self):
        "Returns an ErrorDict for self.data"
        if self.__errors is None:
            self._validate()
        return self.__errors

    def is_valid(self):
        """
        Returns True if the form has no errors. Otherwise, False. This exists
        solely for convenience, so client code can use positive logic rather
        than confusing negative logic ("if not form.errors()").
        """
        return not bool(self.errors())

    def __getitem__(self, name):
        "Returns a BoundField with the given name."
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError('Key %r not found in Form' % name)
        return BoundField(self, field, name)

    def _validate(self):
        data_python = {}
        errors = ErrorDict()
        for name, field in self.fields.items():
            try:
                value = field.to_python(self.data.get(name, None))
                data_python[name] = value
            except ValidationError, e:
                errors[name] = e.messages
        if not errors: # Only set self.data_python if there weren't errors.
            self.__data_python = data_python
        self.__errors = errors

class BoundField(object):
    "A Field plus data"
    def __init__(self, form, field, name):
        self._form = form
        self._field = field
        self._name = name

    def __str__(self):
        "Renders this field as an HTML widget."
        # Use the 'widget' attribute on the field to determine which type
        # of HTML widget to use.
        return self.as_widget(self._field.widget)

    def _errors(self):
        """
        Returns an ErrorList for this field. Returns an empty ErrorList
        if there are none.
        """
        try:
            return self._form.errors()[self._name]
        except KeyError:
            return ErrorList()
    errors = property(_errors)

    def as_widget(self, widget, attrs=None):
        return widget.render(self._name, self._form.data.get(self._name, None), attrs=attrs)

    def as_text(self, attrs=None):
        """
        Returns a string of HTML for representing this as an <input type="text">.
        """
        return self.as_widget(TextInput(), attrs)

    def as_textarea(self, attrs=None):
        "Returns a string of HTML for representing this as a <textarea>."
        return self.as_widget(Textarea(), attrs)

##########################
# DATABASE API SHORTCUTS #
##########################

def form_for_model(model):
    "Returns a Form instance for the given Django model class."
    raise NotImplementedError

def form_for_fields(field_list):
    "Returns a Form instance for the given list of Django database field instances."
    raise NotImplementedError

if __name__ == "__main__":
    import doctest
    doctest.testmod()
