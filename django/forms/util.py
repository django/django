from django.conf import settings
from django.utils.html import conditional_escape
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

# Import ValidationError so that it can be imported from this
# module to maintain backwards compatibility.
from django.core.exceptions import ValidationError

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
                % ''.join([u'<li>%s%s</li>' % (k, conditional_escape(force_unicode(v)))
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
                % ''.join([u'<li>%s</li>' % conditional_escape(force_unicode(e)) for e in self]))

    def as_text(self):
        if not self: return u''
        return u'\n'.join([u'* %s' % force_unicode(e) for e in self])

    def __repr__(self):
        return repr([force_unicode(e) for e in self])

# Utilities for time zone support in DateTimeField et al.

def from_current_timezone(value):
    """
    When time zone support is enabled, convert naive datetimes
    entered in the current time zone to aware datetimes.
    """
    if settings.USE_TZ and value is not None and timezone.is_naive(value):
        current_timezone = timezone.get_current_timezone()
        try:
            return timezone.make_aware(value, current_timezone)
        except Exception, e:
            raise ValidationError(_('%(datetime)s couldn\'t be interpreted '
                                    'in time zone %(current_timezone)s; it '
                                    'may be ambiguous or it may not exist.')
                                  % {'datetime': value,
                                     'current_timezone': current_timezone})
    return value

def to_current_timezone(value):
    """
    When time zone support is enabled, convert aware datetimes
    to naive dateimes in the current time zone for display.
    """
    if settings.USE_TZ and value is not None and timezone.is_aware(value):
        current_timezone = timezone.get_current_timezone()
        return timezone.make_naive(value, current_timezone)
    return value
