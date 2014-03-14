from __future__ import unicode_literals

import json
import sys
import warnings

try:
    from collections import UserList
except ImportError:  # Python 2
    from UserList import UserList

from django.conf import settings
from django.utils.deprecation import RemovedInDjango18Warning
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.html import format_html, format_html_join, escape
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils import six

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
    for attr_name, value in attrs.items():
        if type(value) is bool:
            warnings.warn(
                "In Django 1.8, widget attribute %(attr_name)s=%(bool_value)s "
                "will %(action)s. To preserve current behavior, use the "
                "string '%(bool_value)s' instead of the boolean value." % {
                    'attr_name': attr_name,
                    'action': "be rendered as '%s'" % attr_name if value else "not be rendered",
                    'bool_value': value,
                },
                RemovedInDjango18Warning
            )
    return format_html_join('', ' {0}="{1}"', sorted(attrs.items()))


@python_2_unicode_compatible
class ErrorDict(dict):
    """
    A collection of errors that knows how to display itself in various formats.

    The dictionary keys are the field names, and the values are the errors.
    """
    def as_data(self):
        return {f: e.as_data() for f, e in self.items()}

    def as_json(self, escape_html=False):
        return json.dumps({f: e.get_json_data(escape_html) for f, e in self.items()})

    def as_ul(self):
        if not self:
            return ''
        return format_html(
            '<ul class="errorlist">{0}</ul>',
            format_html_join('', '<li>{0}{1}</li>', ((k, force_text(v)) for k, v in self.items()))
        )

    def as_text(self):
        output = []
        for field, errors in self.items():
            output.append('* %s' % field)
            output.append('\n'.join('  * %s' % e for e in errors))
        return '\n'.join(output)

    def __str__(self):
        return self.as_ul()


@python_2_unicode_compatible
class ErrorList(UserList, list):
    """
    A collection of errors that knows how to display itself in various formats.
    """
    def as_data(self):
        return ValidationError(self.data).error_list

    def get_json_data(self, escape_html=False):
        errors = []
        for error in self.as_data():
            message = list(error)[0]
            errors.append({
                'message': escape(message) if escape_html else message,
                'code': error.code or '',
            })
        return errors

    def as_json(self, escape_html=False):
        return json.dumps(self.get_json_data(escape_html))

    def as_ul(self):
        if not self.data:
            return ''
        return format_html(
            '<ul class="errorlist">{0}</ul>',
            format_html_join('', '<li>{0}</li>', ((force_text(e),) for e in self))
        )

    def as_text(self):
        return '\n'.join('* %s' % e for e in self)

    def __str__(self):
        return self.as_ul()

    def __repr__(self):
        return repr(list(self))

    def __contains__(self, item):
        return item in list(self)

    def __eq__(self, other):
        return list(self) == other

    def __ne__(self, other):
        return list(self) != other

    def __getitem__(self, i):
        error = self.data[i]
        if isinstance(error, ValidationError):
            return list(error)[0]
        return force_text(error)


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
            message = _(
                '%(datetime)s couldn\'t be interpreted '
                'in time zone %(current_timezone)s; it '
                'may be ambiguous or it may not exist.'
            )
            params = {'datetime': value, 'current_timezone': current_timezone}
            six.reraise(ValidationError, ValidationError(
                message,
                code='ambiguous_timezone',
                params=params,
            ), sys.exc_info()[2])
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
