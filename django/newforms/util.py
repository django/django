from django.conf import settings
from django.utils.html import escape

# Converts a dictionary to a single string with key="value", XML-style with
# a leading space. Assumes keys do not need to be XML-escaped.
flatatt = lambda attrs: u''.join([u' %s="%s"' % (k, escape(v)) for k, v in attrs.items()])

def smart_unicode(s):
    if not isinstance(s, basestring):
        s = unicode(str(s))
    elif not isinstance(s, unicode):
        s = unicode(s, settings.DEFAULT_CHARSET)
    return s

class StrAndUnicode(object):
    """
    A class whose __str__ returns its __unicode__ as a bytestring
    according to settings.DEFAULT_CHARSET.

    Useful as a mix-in.
    """
    def __str__(self):
        return self.__unicode__().encode(settings.DEFAULT_CHARSET)

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
