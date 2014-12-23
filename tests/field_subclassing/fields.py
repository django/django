from __future__ import unicode_literals

import json
import warnings

from django.db import models
from django.utils.encoding import force_text
from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import python_2_unicode_compatible


# Catch warning about subfieldbase  -- remove in Django 2.0
warnings.filterwarnings(
    'ignore',
    'SubfieldBase has been deprecated. Use Field.from_db_value instead.',
    RemovedInDjango20Warning
)


@python_2_unicode_compatible
class Small(object):
    """
    A simple class to show that non-trivial Python objects can be used as
    attributes.
    """
    def __init__(self, first, second):
        self.first, self.second = first, second

    def __str__(self):
        return '%s%s' % (force_text(self.first), force_text(self.second))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.first == other.first and self.second == other.second
        return False


class SmallField(six.with_metaclass(models.SubfieldBase, models.Field)):
    """
    Turns the "Small" class into a Django field. Because of the similarities
    with normal character fields and the fact that Small.__unicode__ does
    something sensible, we don't need to implement a lot here.
    """

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 2
        super(SmallField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField'

    def to_python(self, value):
        if isinstance(value, Small):
            return value
        return Small(value[0], value[1])

    def get_db_prep_save(self, value, connection):
        return six.text_type(value)

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'exact':
            return force_text(value)
        if lookup_type == 'in':
            return [force_text(v) for v in value]
        if lookup_type == 'isnull':
            return []
        raise TypeError('Invalid lookup type: %r' % lookup_type)


class SmallerField(SmallField):
    pass


class JSONField(six.with_metaclass(models.SubfieldBase, models.TextField)):

    description = ("JSONField automatically serializes and deserializes values to "
        "and from JSON.")

    def to_python(self, value):
        if not value:
            return None

        if isinstance(value, six.string_types):
            value = json.loads(value)
        return value

    def get_db_prep_save(self, value, connection):
        if value is None:
            return None
        return json.dumps(value)


class CustomTypedField(models.TextField):
    def db_type(self, connection):
        return 'custom_field'

from django.utils.translation import ugettext_lazy as _
from django.db.models import fields
import six


class CustomAutoField(fields.Field):
    description = _("Integer")

    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%(value)s' value must be an integer."),
    }

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        super(CustomAutoField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "AutoField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
            value = connection.ops.validate_autopk_value(value)
        return value

    def get_prep_value(self, value):
        value = super(CustomAutoField, self).get_prep_value(value)
        if value is None:
            return None
        return int(value)

    def contribute_to_class(self, cls, name, **kwargs):
        assert not cls._meta.has_auto_field, \
            "A model can't have more than one AutoField."
        super(CustomAutoField, self).contribute_to_class(cls, name, **kwargs)
        cls._meta.has_auto_field = True
        cls._meta.auto_field = self

    def formfield(self, **kwargs):
        return None
