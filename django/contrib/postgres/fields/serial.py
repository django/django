from django.contrib.postgres.expressions import Default
from django.db.models import PositiveIntegerField
from django.utils.translation import ugettext_lazy as _


class SerialField(PositiveIntegerField):
    description = _("Serial")

    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        kwargs.setdefault('unique', True)
        kwargs.setdefault('editable', False)
        super(SerialField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop('blank')
        return name, path, args, kwargs

    def get_internal_type(self):
        return "SerialField"

    def get_default(self):
        return Default()


class SmallSerialField(SerialField):
    description = _("SmallSerial")

    def get_internal_type(self):
        return "SmallSerialField"


class BigSerialField(SerialField):
    description = _("BigSerial")

    def get_internal_type(self):
        return "BigSerialField"
