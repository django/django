from __future__ import unicode_literals

from django.conf import settings
from django.utils.html import format_html, format_html_join
from django.utils.encoding import force_text, python_2_unicode_compatible
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

    The result is passed through 'mark_safe'.
    """
    return format_html_join('', ' {0}="{1}"', sorted(attrs.items()))

@python_2_unicode_compatible
class ErrorDict(dict):
    """
    A collection of errors that knows how to display itself in various formats.

    The dictionary keys are the field names, and the values are the errors.
    """
    def __str__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return ''
        return format_html('<ul class="errorlist">{0}</ul>',
                           format_html_join('', '<li>{0}{1}</li>',
                                            ((k, force_text(v))
                                             for k, v in self.items())
                           ))

    def as_text(self):
        return '\n'.join(['* %s\n%s' % (k, '\n'.join(['  * %s' % force_text(i) for i in v])) for k, v in self.items()])

@python_2_unicode_compatible
class ErrorList(list):
    """
    A collection of errors that knows how to display itself in various formats.
    """
    def __str__(self):
        return self.as_ul()

    def as_ul(self):
        if not self: return ''
        return format_html('<ul class="errorlist">{0}</ul>',
                           format_html_join('', '<li>{0}</li>',
                                            ((force_text(e),) for e in self)
                                            )
                           )

    def as_text(self):
        if not self: return ''
        return '\n'.join(['* %s' % force_text(e) for e in self])

    def __repr__(self):
        return repr([force_text(e) for e in self])

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
        except Exception:
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
