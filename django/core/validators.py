import re
import urllib2
import urlparse

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

# These values, if given to validate(), will trigger the self.required check.
EMPTY_VALUES = (None, '', [], (), {})

try:
    from django.conf import settings
    URL_VALIDATOR_USER_AGENT = settings.URL_VALIDATOR_USER_AGENT
except ImportError:
    # It's OK if Django settings aren't configured.
    URL_VALIDATOR_USER_AGENT = 'Django (http://www.djangoproject.com/)'

class RegexValidator(object):
    regex = ''
    message = _(u'Enter a valid value.')
    code = 'invalid'

    def __init__(self, regex=None, message=None, code=None):
        if regex is not None:
            self.regex = regex
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

        if isinstance(self.regex, basestring):
            self.regex = re.compile(regex)

    def __call__(self, value):
        """
        Validates that the input matches the regular expression.
        """
        if not self.regex.search(smart_unicode(value)):
            raise ValidationError(self.message, code=self.code)

class HeadRequest(urllib2.Request):
    def get_method(self):
        return "HEAD"

class URLValidator(RegexValidator):
    regex = re.compile(
        r'^https?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    def __init__(self, verify_exists=False, validator_user_agent=URL_VALIDATOR_USER_AGENT):
        super(URLValidator, self).__init__()
        self.verify_exists = verify_exists
        self.user_agent = validator_user_agent

    def __call__(self, value):
        try:
            super(URLValidator, self).__call__(value)
        except ValidationError, e:
            # Trivial case failed. Try for possible IDN domain
            if value:
                value = smart_unicode(value)
                scheme, netloc, path, query, fragment = urlparse.urlsplit(value)
                try:
                    netloc = netloc.encode('idna') # IDN -> ACE
                except UnicodeError: # invalid domain part
                    raise e
                url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))
                super(URLValidator, self).__call__(url)
            else:
                raise
        else:
            url = value

        if self.verify_exists:
            headers = {
                "Accept": "text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                "Connection": "close",
                "User-Agent": self.user_agent,
            }
            broken_error = ValidationError(
                _(u'This URL appears to be a broken link.'), code='invalid_link')
            try:
                req = HeadRequest(url, None, headers)
                u = urllib2.urlopen(req)
            except ValueError:
                raise ValidationError(_(u'Enter a valid URL.'), code='invalid')
            except urllib2.HTTPError, e:
                if e.code in (405, 501):
                    # Try a GET request (HEAD refused)
                    # See also: http://www.w3.org/Protocols/rfc2616/rfc2616.html
                    try:
                        req = urllib2.Request(url, None, headers)
                        u = urllib2.urlopen(req)
                    except:
                        raise broken_error
                else:
                    raise broken_error
            except: # urllib2.URLError, httplib.InvalidURL, etc.
                raise broken_error


def validate_integer(value):
    try:
        int(value)
    except (ValueError, TypeError), e:
        raise ValidationError('')

class EmailValidator(RegexValidator):

    def __call__(self, value):
        try:
            super(EmailValidator, self).__call__(value)
        except ValidationError, e:
            # Trivial case failed. Try for possible IDN domain-part
            if value and u'@' in value:
                parts = value.split(u'@')
                domain_part = parts[-1]
                try:
                    parts[-1] = parts[-1].encode('idna')
                except UnicodeError:
                    raise e
                super(EmailValidator, self).__call__(u'@'.join(parts))
            else:
                raise

email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE)  # domain
validate_email = EmailValidator(email_re, _(u'Enter a valid e-mail address.'), 'invalid')

slug_re = re.compile(r'^[-\w]+$')
validate_slug = RegexValidator(slug_re, _(u"Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens."), 'invalid')

ipv4_re = re.compile(r'^(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}$')
validate_ipv4_address = RegexValidator(ipv4_re, _(u'Enter a valid IPv4 address.'), 'invalid')

comma_separated_int_list_re = re.compile('^[\d,]+$')
validate_comma_separated_integer_list = RegexValidator(comma_separated_int_list_re, _(u'Enter only digits separated by commas.'), 'invalid')


class BaseValidator(object):
    compare = lambda self, a, b: a is not b
    clean   = lambda self, x: x
    message = _(u'Ensure this value is %(limit_value)s (it is %(show_value)s).')
    code = 'limit_value'

    def __init__(self, limit_value):
        self.limit_value = limit_value

    def __call__(self, value):
        cleaned = self.clean(value)
        params = {'limit_value': self.limit_value, 'show_value': cleaned}
        if self.compare(cleaned, self.limit_value):
            raise ValidationError(
                self.message % params,
                code=self.code,
                params=params,
            )

class MaxValueValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    message = _(u'Ensure this value is less than or equal to %(limit_value)s.')
    code = 'max_value'

class MinValueValidator(BaseValidator):
    compare = lambda self, a, b: a < b
    message = _(u'Ensure this value is greater than or equal to %(limit_value)s.')
    code = 'min_value'

class MinLengthValidator(BaseValidator):
    compare = lambda self, a, b: a < b
    clean   = lambda self, x: len(x)
    message = _(u'Ensure this value has at least %(limit_value)d characters (it has %(show_value)d).')
    code = 'min_length'

class MaxLengthValidator(BaseValidator):
    compare = lambda self, a, b: a > b
    clean   = lambda self, x: len(x)
    message = _(u'Ensure this value has at most %(limit_value)d characters (it has %(show_value)d).')
    code = 'max_length'

