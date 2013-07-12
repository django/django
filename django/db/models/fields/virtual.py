from __future__ import unicode_literals

from django.db.models.fields import Field


class VirtualField(Field):
    """
    Base class for field types with no direct database representation.
    """
    def __init__(self, **kwargs):
        kwargs.setdefault('serialize', False)
        kwargs.setdefault('editable', False)
        super(VirtualField, self).__init__(**kwargs)

    def db_type(self, connection):
        return None

    def contribute_to_class(self, cls, name):
        super(VirtualField, self).contribute_to_class(cls, name)
        # Virtual fields are descriptors; they are not handled
        # individually at instance level.
        setattr(cls, name, self)

    def get_column(self):
        return None

    def get_enclosed_fields(self):
        return []

    def resolve_basic_fields(self):
        return [f
                for myfield in self.get_enclosed_fields()
                for f in myfield.resolve_basic_fields()]

    def formfield(self):
        return None

    def __get__(self, instance, owner):
        return None

    def __set__(self, instance, value):
        pass
