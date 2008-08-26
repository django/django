from django.utils.html import conditional_escape
from django.utils.encoding import smart_unicode, StrAndUnicode, force_unicode
from django.utils.safestring import mark_safe

def flatatt(attrs):
    """
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs.  It is assumed that the keys do not need to be XML-escaped.
    If the passed dictionary is empty, then return an empty string.
    """
    return u''.join([u' %s="%s"' % (k, conditional_escape(v)) for k, v in attrs.items()])

class ErrorDict(dict, StrAndUnicode):
    """
    A collection of errors that knows how to display itself in various formats.

    The dictionary keys are the field names, and the values are the errors.
    """
    def __unicode__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return u''
        return mark_safe(u'<ul class="errorlist">%s</ul>'
                % ''.join([u'<li>%s%s</li>' % (k, force_unicode(v))
                    for k, v in self.items()]))

    def as_text(self):
        return u'\n'.join([u'* %s\n%s' % (k, u'\n'.join([u'  * %s' % force_unicode(i) for i in v])) for k, v in self.items()])

class ErrorList(list, StrAndUnicode):
    """
    A collection of errors that knows how to display itself in various formats.
    """
    def __unicode__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return u''
        return mark_safe(u'<ul class="errorlist">%s</ul>'
                % ''.join([u'<li>%s</li>' % force_unicode(e) for e in self]))

    def as_text(self):
        if not self: return u''
        return u'\n'.join([u'* %s' % force_unicode(e) for e in self])

    def __repr__(self):
        return repr([force_unicode(e) for e in self])

class ValidationError(Exception):
    def __init__(self, message):
        """
        ValidationError can be passed any object that can be printed (usually
        a string) or a list of objects.
        """
        if isinstance(message, list):
            self.messages = ErrorList([smart_unicode(msg) for msg in message])
        else:
            message = smart_unicode(message)
            self.messages = ErrorList([message])

    def __str__(self):
        # This is needed because, without a __str__(), printing an exception
        # instance would result in this:
        # AttributeError: ValidationError instance has no attribute 'args'
        # See http://www.python.org/doc/current/tut/node10.html#handling
        return repr(self.messages)
