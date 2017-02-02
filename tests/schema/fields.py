from django.db import models
from django.db.models.fields.related import (
    RECURSIVE_RELATIONSHIP_CONSTANT, ManyToManyDescriptor, ManyToManyField,
    ManyToManyRel, RelatedField, create_many_to_many_intermediary_model,
)
from django.utils.functional import curry


class CustomManyToManyField(RelatedField):
    """
    Ticket #24104 - Need to have a custom ManyToManyField,
    which is not an inheritor of ManyToManyField.
    """
    many_to_many = True

    def __init__(self, to, db_constraint=True, swappable=True, related_name=None, related_query_name=None,
                 limit_choices_to=None, symmetrical=None, through=None, through_fields=None, db_table=None, **kwargs):
        try:
            to._meta
        except AttributeError:
            to = str(to)
        kwargs['rel'] = ManyToManyRel(
            self, to,
            related_name=related_name,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            symmetrical=symmetrical if symmetrical is not None else (to == RECURSIVE_RELATIONSHIP_CONSTANT),
            through=through,
            through_fields=through_fields,
            db_constraint=db_constraint,
        )
        self.swappable = swappable
        self.db_table = db_table
        if kwargs['rel'].through is not None:
            assert self.db_table is None, "Cannot specify a db_table if an intermediary model is used."
        super().__init__(**kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        if self.remote_field.symmetrical and (
                self.remote_field.model == "self" or self.remote_field.model == cls._meta.object_name):
            self.remote_field.related_name = "%s_rel_+" % name
        super().contribute_to_class(cls, name, **kwargs)
        if not self.remote_field.through and not cls._meta.abstract and not cls._meta.swapped:
            self.remote_field.through = create_many_to_many_intermediary_model(self, cls)
        setattr(cls, self.name, ManyToManyDescriptor(self.remote_field))
        self.m2m_db_table = curry(self._get_m2m_db_table, cls._meta)

    def get_internal_type(self):
        return 'ManyToManyField'

    # Copy those methods from ManyToManyField because they don't call super() internally
    contribute_to_related_class = ManyToManyField.__dict__['contribute_to_related_class']
    _get_m2m_attr = ManyToManyField.__dict__['_get_m2m_attr']
    _get_m2m_reverse_attr = ManyToManyField.__dict__['_get_m2m_reverse_attr']
    _get_m2m_db_table = ManyToManyField.__dict__['_get_m2m_db_table']


class InheritedManyToManyField(ManyToManyField):
    pass


class MediumBlobField(models.BinaryField):
    """
    A MySQL BinaryField that uses a different blob size.
    """
    def db_type(self, connection):
        return 'MEDIUMBLOB'
