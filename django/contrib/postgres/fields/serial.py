from django.db import models
from django.db.models.expressions import DatabaseDefault, Expression
from django.utils.translation import gettext_lazy as _

__all__ = ("BigSerialField", "SmallSerialField", "SerialField")


class NextSerialSequence(Expression):
    allowed_default = True

    def as_sql(self, compiler, connection):
        table = self.field.model._meta.db_table
        column = self.field.column
        return "nextval(pg_get_serial_sequence(%s, %s))", [table, column]


class SerialFieldMixin:
    db_returning = True

    def __init__(self, *args, **kwargs):
        default = DatabaseDefault()
        db_default = NextSerialSequence(self)

        if not kwargs.setdefault("blank", True):
            raise ValueError(f"{self.__class__.__name__} must be blank.")
        if kwargs.setdefault("null", False):
            raise ValueError(f"{self.__class__.__name__} must not be null.")
        if kwargs.setdefault("default", default) is not default:
            raise ValueError(f"{self.__class__.__name__} cannot have a default.")
        if kwargs.setdefault("db_default", db_default) is not db_default:
            raise ValueError(
                f"{self.__class__.__name__} cannot have a database default."
            )

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["default"]
        del kwargs["db_default"]
        return name, path, args, kwargs

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            value = self.get_default()
        return value


class BigSerialField(SerialFieldMixin, models.BigIntegerField):
    description = _("Big serial")

    def get_internal_type(self):
        return "BigSerialField"

    def db_type(self, connection):
        return "bigserial"

    def rel_db_type(self, connection):
        return "bigint"


class SmallSerialField(SerialFieldMixin, models.SmallIntegerField):
    description = _("Small serial")

    def get_internal_type(self):
        return "SmallSerialField"

    def db_type(self, connection):
        return "smallserial"

    def rel_db_type(self, connection):
        return "smallint"


class SerialField(SerialFieldMixin, models.IntegerField):
    description = _("Serial")

    def get_internal_type(self):
        return "SerialField"

    def db_type(self, connection):
        return "serial"

    def rel_db_type(self, connection):
        return "integer"
