from django.db import models
from django.db.models.expressions import Default
from django.utils.translation import gettext_lazy as _

__all__ = ('BigSerialField', 'SmallSerialField', 'SerialField')


class SerialFieldMixin:
    db_returning = True
    uses_sequence = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **{
            **kwargs,
            'blank': True,
            'default': Default(),
            'null': False,
        })

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop('blank')
        kwargs.pop('default')
        return name, path, args, kwargs


class BigSerialField(SerialFieldMixin, models.BigIntegerField):
    description = _('Big serial')

    def get_internal_type(self):
        return 'BigSerialField'

    def db_type(self, connection):
        return 'bigserial'


class SmallSerialField(SerialFieldMixin, models.SmallIntegerField):
    description = _('Small serial')

    def get_internal_type(self):
        return 'SmallSerialField'

    def db_type(self, connection):
        return 'smallserial'


class SerialField(SerialFieldMixin, models.IntegerField):
    description = _('Serial')

    def get_internal_type(self):
        return 'SerialField'

    def db_type(self, connection):
        return 'serial'
