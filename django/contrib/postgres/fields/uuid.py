from django.contrib.postgres.functions import RandomUUID
from django.db.models import UUIDField
from django.db.models.fields import NOT_PROVIDED, AutoFieldMixin


class UUID4Field(UUIDField):
    def __init__(self, *args, **kwargs):
        kwargs["db_default"] = RandomUUID()
        kwargs["default"] = NOT_PROVIDED
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return "UUID4Field"


class UUID4AutoField(AutoFieldMixin, UUID4Field):
    def get_internal_type(self):
        return "UUID4AutoField"
