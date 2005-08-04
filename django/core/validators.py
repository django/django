"""
A library of validators that return None and raise ValidationError when the
provided data isn't valid.

Validators may be callable classes, and they may have an 'always_test'
attribute. If an 'always_test' attribute exists (regardless of value), the
validator will *always* be run, regardless of whether its associated
form field is required.
"""

import re

_datere = r'\d{4}-((?:0?[1-9])|(?:1[0-2]))-((?:0?[1-9])|(?:[12][0-9])|(?:3[0-1]))'
_timere = r'(?:[01]?[0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?'
alnum_re = re.compile(r'^\w+$')
alnumurl_re = re.compile(r'^[\w/]+$')
ansi_date_re = re.compile('^%s$' % _datere)
ansi_time_re = re.compile('^%s$' % _timere)
ansi_datetime_re = re.compile('^%s %s$' % (_datere, _timere))
email_re = re.compile(r'^[-\w.+]+@\w[\w.-]+$')
integer_re = re.compile(r'^-?\d+$')
phone_re = re.compile(r'^[A-PR-Y0-9]{3}-[A-PR-Y0-9]{3}-[A-PR-Y0-9]{4}$', re.IGNORECASE)
url_re = re.compile(r'^http://\S+$')

JING = '/usr/bin/jing'

class ValidationError(Exception):
    def __init__(self, message):
        "ValidationError can be passed a string or a list."
        if isinstance(message, list):
            self.messages = message
        else:
            assert isinstance(message, basestring), ("%s should be a string" % repr(message))
            self.messages = [message]
    def __str__(self):
        # This is needed because, without a __str__(), printing an exception
        # instance would result in this:
        # AttributeError: ValidationError instance has no attribute 'args'
        # See http://www.python.org/doc/current/tut/node10.html#handling
        return str(self.messages)

class CriticalValidationError(Exception):
    def __init__(self, message):
        "ValidationError can be passed a string or a list."
        if isinstance(message, list):
            self.messages = message
        else:
            assert isinstance(message, basestring), ("'%s' should be a string" % message)
            self.messages = [message]
    def __str__(self):
        return str(self.messages)

def isAlphaNumeric(field_data, all_data):
    if not alnum_re.search(field_data):
        raise ValidationError, "This value must contain only letters, numbers and underscores."

def isAlphaNumericURL(field_data, all_data):
    if not alnumurl_re.search(field_data):
        raise ValidationError, "This value must contain only letters, numbers, underscores and slashes."

def isLowerCase(field_data, all_data):
    if field_data.lower() != field_data:
        raise ValidationError, "Uppercase letters are not allowed here."

def isUpperCase(field_data, all_data):
    if field_data.upper() != field_data:
        raise ValidationError, "Lowercase letters are not allowed here."

def isCommaSeparatedIntegerList(field_data, all_data):
    for supposed_int in field_data.split(','):
        try:
            int(supposed_int)
        except ValueError:
            raise ValidationError, "Enter only digits separated by commas."

def isCommaSeparatedEmailList(field_data, all_data):
    """
    Checks that field_data is a string of e-mail addresses separated by commas.
    Blank field_data values will not throw a validation error, and whitespace
    is allowed around the commas.
    """
    for supposed_email in field_data.split(','):
        try:
            isValidEmail(supposed_email.strip(), '')
        except ValidationError:
            raise ValidationError, "Enter valid e-mail addresses separated by commas."

def isNotEmpty(field_data, all_data):
    if field_data.strip() == '':
        raise ValidationError, "Empty values are not allowed here."

def isOnlyDigits(field_data, all_data):
    if not field_data.isdigit():
        raise ValidationError, "Non-numeric characters aren't allowed here."

def isNotOnlyDigits(field_data, all_data):
    if field_data.isdigit():
        raise ValidationError, "This value can't be comprised solely of digits."

def isInteger(field_data, all_data):
    # This differs from isOnlyDigits because this accepts the negative sign
    if not integer_re.search(field_data):
        raise ValidationError, "Enter a whole number."

def isOnlyLetters(field_data, all_data):
    if not field_data.isalpha():
        raise ValidationError, "Only alphabetical characters are allowed here."

def isValidANSIDate(field_data, all_data):
    if not ansi_date_re.search(field_data):
        raise ValidationError, 'Enter a valid date in YYYY-MM-DD format.'

def isValidANSITime(field_data, all_data):
    if not ansi_time_re.search(field_data):
        raise ValidationError, 'Enter a valid time in HH:MM format.'

def isValidANSIDatetime(field_data, all_data):
    if not ansi_datetime_re.search(field_data):
        raise ValidationError, 'Enter a valid date/time in YYYY-MM-DD HH:MM format.'

def isValidEmail(field_data, all_data):
    if not email_re.search(field_data):
        raise ValidationError, 'Enter a valid e-mail address.'

def isValidImage(field_data, all_data):
    """
    Checks that the file-upload field data contains a valid image (GIF, JPG,
    PNG, possibly others -- whatever the Python Imaging Library supports).
    """
    from PIL import Image
    from cStringIO import StringIO
    try:
        Image.open(StringIO(field_data['content']))
    except IOError: # Python Imaging Library doesn't recognize it as an image
        raise ValidationError, "Upload a valid image. The file you uploaded was either not an image or a corrupted image."

def isValidImageURL(field_data, all_data):
    uc = URLMimeTypeCheck(('image/jpeg', 'image/gif', 'image/png'))
    try:
        uc(field_data, all_data)
    except URLMimeTypeCheck.InvalidContentType:
        raise ValidationError, "The URL %s does not point to a valid image." % field_data

def isValidPhone(field_data, all_data):
    if not phone_re.search(field_data):
        raise ValidationError, 'Phone numbers must be in XXX-XXX-XXXX format. "%s" is invalid.' % field_data

def isValidQuicktimeVideoURL(field_data, all_data):
    "Checks that the given URL is a video that can be played by QuickTime (qt, mpeg)"
    uc = URLMimeTypeCheck(('video/quicktime', 'video/mpeg',))
    try:
        uc(field_data, all_data)
    except URLMimeTypeCheck.InvalidContentType:
        raise ValidationError, "The URL %s does not point to a valid QuickTime video." % field_data

def isValidURL(field_data, all_data):
    if not url_re.search(field_data):
        raise ValidationError, "A valid URL is required."

def isWellFormedXml(field_data, all_data):
    from xml.dom.minidom import parseString
    try:
        parseString(field_data)
    except Exception, e: # Naked except because we're not sure what will be thrown
        raise ValidationError, "Badly formed XML: %s" % str(e)

def isWellFormedXmlFragment(field_data, all_data):
    isWellFormedXml('<root>%s</root>' % field_data, all_data)

def isExistingURL(field_data, all_data):
    import urllib2
    try:
        u = urllib2.urlopen(field_data)
    except ValueError:
        raise ValidationError, "Invalid URL: %s" % field_data
    except: # urllib2.HTTPError, urllib2.URLError, httplib.InvalidURL, etc.
        raise ValidationError, "The URL %s is a broken link." % field_data

def isValidUSState(field_data, all_data):
    "Checks that the given string is a valid two-letter U.S. state abbreviation"
    states = ['AA', 'AE', 'AK', 'AL', 'AP', 'AR', 'AS', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL', 'FM', 'GA', 'GU', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA', 'MA', 'MD', 'ME', 'MH', 'MI', 'MN', 'MO', 'MP', 'MS', 'MT', 'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK', 'OR', 'PA', 'PR', 'PW', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA', 'VI', 'VT', 'WA', 'WI', 'WV', 'WY']
    if field_data.upper() not in states:
        raise ValidationError, "Enter a valid U.S. state abbreviation."

def hasNoProfanities(field_data, all_data):
    """
    Checks that the given string has no profanities in it. This does a simple
    check for whether each profanity exists within the string, so 'fuck' will
    catch 'motherfucker' as well. Raises a ValidationError such as:
        Watch your mouth! The words "f--k" and "s--t" are not allowed here.
    """
    bad_words = ['asshat', 'asshead', 'asshole', 'cunt', 'fuck', 'gook', 'nigger', 'shit'] # all in lower case
    field_data = field_data.lower() # normalize
    words_seen = [w for w in bad_words if field_data.find(w) > -1]
    if words_seen:
        from django.utils.text import get_text_list
        plural = len(words_seen) > 1
        raise ValidationError, "Watch your mouth! The word%s %s %s not allowed here." % \
            (plural and 's' or '',
            get_text_list(['"%s%s%s"' % (i[0], '-'*(len(i)-2), i[-1]) for i in words_seen], 'and'),
            plural and 'are' or 'is')

class AlwaysMatchesOtherField:
    def __init__(self, other_field_name, error_message=None):
        self.other = other_field_name
        self.error_message = error_message or "This field must match the '%s' field." % self.other
        self.always_test = True

    def __call__(self, field_data, all_data):
        if field_data != all_data[self.other]:
            raise ValidationError, self.error_message

class RequiredIfOtherFieldGiven:
    def __init__(self, other_field_name, error_message=None):
        self.other = other_field_name
        self.error_message = error_message or "Please enter both fields or leave them both empty."
        self.always_test = True

    def __call__(self, field_data, all_data):
        if all_data[self.other] and not field_data:
            raise ValidationError, self.error_message

class RequiredIfOtherFieldNotGiven:
    def __init__(self, other_field_name, error_message=None):
        self.other = other_field_name
        self.error_message = error_message or "Please enter something for at least one field."
        self.always_test = True

    def __call__(self, field_data, all_data):
        if not all_data.get(self.other, False) and not field_data:
            raise ValidationError, self.error_message

class RequiredIfOtherFieldsGiven:
    "Like RequiredIfOtherFieldGiven, but takes a list of required field names instead of a single field name"
    def __init__(self, other_field_names, error_message=None):
        self.other = other_field_names
        self.error_message = error_message or "Please enter both fields or leave them both empty."
        self.always_test = True

    def __call__(self, field_data, all_data):
        for field in self.other:
            if all_data.has_key(field) and all_data[field] and not field_data:
                raise ValidationError, self.error_message

class RequiredIfOtherFieldEquals:
    def __init__(self, other_field, other_value, error_message=None):
        self.other_field = other_field
        self.other_value = other_value
        self.error_message = error_message or "This field must be given if %s is %s" % (other_field, other_value)
        self.always_test = True

    def __call__(self, field_data, all_data):
        if all_data.has_key(self.other_field) and all_data[self.other_field] == self.other_value and not field_data:
            raise ValidationError(self.error_message)

class RequiredIfOtherFieldDoesNotEqual:
    def __init__(self, other_field, other_value, error_message=None):
        self.other_field = other_field
        self.other_value = other_value
        self.error_message = error_message or "This field must be given if %s is not %s" % (other_field, other_value)
        self.always_test = True

    def __call__(self, field_data, all_data):
        if all_data.has_key(self.other_field) and all_data[self.other_field] != self.other_value and not field_data:
            raise ValidationError(self.error_message)

class IsLessThanOtherField:
    def __init__(self, other_field_name, error_message):
        self.other, self.error_message = other_field_name, error_message

    def __call__(self, field_data, all_data):
        if field_data > all_data[self.other]:
            raise ValidationError, self.error_message

class UniqueAmongstFieldsWithPrefix:
    def __init__(self, field_name, prefix, error_message):
        self.field_name, self.prefix = field_name, prefix
        self.error_message = error_message or "Duplicate values are not allowed."

    def __call__(self, field_data, all_data):
        for field_name, value in all_data.items():
            if field_name != self.field_name and value == field_data:
                raise ValidationError, self.error_message

class IsAPowerOf:
    """
    >>> v = IsAPowerOf(2)
    >>> v(4, None)
    >>> v(8, None)
    >>> v(16, None)
    >>> v(17, None)
    django.core.validators.ValidationError: ['This value must be a power of 2.']
    """
    def __init__(self, power_of):
        self.power_of = power_of

    def __call__(self, field_data, all_data):
        from math import log
        val = log(int(field_data)) / log(self.power_of)
        if val != int(val):
            raise ValidationError, "This value must be a power of %s." % self.power_of

class IsValidFloat:
    def __init__(self, max_digits, decimal_places):
        self.max_digits, self.decimal_places = max_digits, decimal_places

    def __call__(self, field_data, all_data):
        data = str(field_data)
        try:
            float(data)
        except ValueError:
            raise ValidationError, "Please enter a valid decimal number."
        if len(data) > (self.max_digits + 1):
            raise ValidationError, "Please enter a valid decimal number with at most %s total digit%s." % \
                (self.max_digits, self.max_digits > 1 and 's' or '')
        if '.' in data and len(data.split('.')[1]) > self.decimal_places:
            raise ValidationError, "Please enter a valid decimal number with at most %s decimal place%s." % \
                (self.decimal_places, self.decimal_places > 1 and 's' or '')

class HasAllowableSize:
    """
    Checks that the file-upload field data is a certain size. min_size and
    max_size are measurements in bytes.
    """
    def __init__(self, min_size=None, max_size=None, min_error_message=None, max_error_message=None):
        self.min_size, self.max_size = min_size, max_size
        self.min_error_message = min_error_message or "Make sure your uploaded file is at least %s bytes big." % min_size
        self.max_error_message = max_error_message or "Make sure your uploaded file is at most %s bytes big." % min_size

    def __call__(self, field_data, all_data):
        if self.min_size is not None and len(field_data['content']) < self.min_size:
            raise ValidationError, self.min_error_message
        if self.max_size is not None and len(field_data['content']) > self.max_size:
            raise ValidationError, self.max_error_message

class MatchesRegularExpression:
    """
    Checks that the field matches the given regular-expression. The regex
    should be in string format, not already compiled.
    """
    def __init__(self, regexp, error_message="The format for this field is wrong."):
        self.regexp = re.compile(regexp)
        self.error_message = error_message

    def __call__(self, field_data, all_data):
        if not self.regexp.match(field_data):
            raise validators.ValidationError(self.error_message)

class URLMimeTypeCheck:
    "Checks that the provided URL points to a document with a listed mime type"
    class CouldNotRetrieve(ValidationError):
        pass
    class InvalidContentType(ValidationError):
        pass

    def __init__(self, mime_type_list):
        self.mime_type_list = mime_type_list

    def __call__(self, field_data, all_data):
        import urllib2
        try:
            isValidURL(field_data, all_data)
        except ValidationError:
            raise
        try:
            info = urllib2.urlopen(field_data).info()
        except (urllib2.HTTPError, urllib2.URLError):
            raise URLMimeTypeCheck.CouldNotRetrieve, "Could not retrieve anything from %s." % field_data
        content_type = info['content-type']
        if content_type not in self.mime_type_list:
            raise URLMimeTypeCheck.InvalidContentType, "The URL %s returned the invalid Content-Type header '%s'." % (field_data, content_type)

class RelaxNGCompact:
    "Validate against a Relax NG compact schema"
    def __init__(self, schema_path, additional_root_element=None):
        self.schema_path = schema_path
        self.additional_root_element = additional_root_element

    def __call__(self, field_data, all_data):
        import os, tempfile
        if self.additional_root_element:
            field_data = '<%(are)s>%(data)s\n</%(are)s>' % {
                'are': self.additional_root_element,
                'data': field_data
            }
        filename = tempfile.mktemp() # Insecure, but nothing else worked
        fp = open(filename, 'w')
        fp.write(field_data)
        fp.close()
        if not os.path.exists(JING):
            raise Exception, "%s not found!" % JING
        p = os.popen('%s -c %s %s' % (JING, self.schema_path, filename))
        errors = [line.strip() for line in p.readlines()]
        p.close()
        os.unlink(filename)
        display_errors = []
        lines = field_data.split('\n')
        for error in errors:
            _, line, level, message = error.split(':', 3)
            # Scrape the Jing error messages to reword them more nicely.
            m = re.search(r'Expected "(.*?)" to terminate element starting on line (\d+)', message)
            if m:
                display_errors.append('Please close the unclosed %s tag from line %s. (Line starts with "%s".)' % \
                    (m.group(1).replace('/', ''), m.group(2), lines[int(m.group(2)) - 1][:30]))
                continue
            if message.strip() == 'text not allowed here':
                display_errors.append('Some text starting on line %s is not allowed in that context. (Line starts with "%s".)' % \
                    (line, lines[int(line) - 1][:30]))
                continue
            m = re.search(r'\s*attribute "(.*?)" not allowed at this point; ignored', message)
            if m:
                display_errors.append('"%s" on line %s is an invalid attribute. (Line starts with "%s".)' % \
                    (m.group(1), line, lines[int(line) - 1][:30]))
                continue
            m = re.search(r'\s*unknown element "(.*?)"', message)
            if m:
                display_errors.append('"<%s>" on line %s is an invalid tag. (Line starts with "%s".)' % \
                    (m.group(1), line, lines[int(line) - 1][:30]))
                continue
            if message.strip() == 'required attributes missing':
                display_errors.append('A tag on line %s is missing one or more required attributes. (Line starts with "%s".)' % \
                    (line, lines[int(line) - 1][:30]))
                continue
            m = re.search(r'\s*bad value for attribute "(.*?)"', message)
            if m:
                display_errors.append('The "%s" attribute on line %s has an invalid value. (Line starts with "%s".)' % \
                    (m.group(1), line, lines[int(line) - 1][:30]))
                continue
            # Failing all those checks, use the default error message.
            display_error = 'Line %s: %s [%s]' % (line, message, level.strip())
            display_errors.append(display_error)
        if len(display_errors) > 0:
            raise ValidationError, display_errors
