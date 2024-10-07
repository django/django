from django.db import models
from django.db.models.query_utils import DeferredAttribute


class CustomTypedField(models.TextField):
    def db_type(self, connection):
        return "custom_field"


class CustomDeferredAttribute(DeferredAttribute):
    def __get__(self, instance, cls=None):
        self._count_call(instance, "get")
        return super().__get__(instance, cls)

    def __set__(self, instance, value):
        self._count_call(instance, "set")
        instance.__dict__[self.field.attname] = value

    def _count_call(self, instance, get_or_set):
        count_attr = "_%s_%s_count" % (self.field.attname, get_or_set)
        count = getattr(instance, count_attr, 0)
        setattr(instance, count_attr, count + 1)


class CustomDescriptorField(models.CharField):
    descriptor_class = CustomDeferredAttribute


class NotOKCustomField(models.CharField):
    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=private_only)

        def get_uppercase_value(instance):
            value = getattr(instance, name)
            return value.upper() if value else value

        setattr(cls, f"get_{name}_uppercase", get_uppercase_value)


class OKCustomField(models.CharField):
    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)

        def get_uppercase_value(instance):
            value = getattr(instance, name)
            return value.upper() if value else value

        setattr(owner, f"get_{name}_uppercase", get_uppercase_value)


class ChildNotOKField(NotOKCustomField):
    pass


class ChildOKField(OKCustomField):
    pass
