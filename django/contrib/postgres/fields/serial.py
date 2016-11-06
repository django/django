from django.db import models
from django.db.models.expressions import Default
from django.utils.translation import gettext_lazy as _

__all__ = ('BigSerialField', 'SmallSerialField', 'SerialField')


class SerialFieldMixin:
    db_returning = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **{
            'editable': False,
            **kwargs,
            'blank': True,
            'default': Default(),
            'unique': True,
        })

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop('blank')
        kwargs.pop('unique')
        kwargs.pop('default')
        if not kwargs.get('editable', True):
            kwargs.pop('editable')
        return name, path, args, kwargs


class BigSerialField(SerialFieldMixin, models.BigIntegerField):
    description = _('Big serial')

    def get_internal_type(self):
        return 'BigSerialField'


class SmallSerialField(SerialFieldMixin, models.SmallIntegerField):
    description = _('Small serial')

    def get_internal_type(self):
        return 'SmallSerialField'


class SerialField(SerialFieldMixin, models.IntegerField):
    description = _('Serial')

    def get_internal_type(self):
        return 'SerialField'
