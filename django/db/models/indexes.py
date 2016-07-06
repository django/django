from __future__ import unicode_literals

import hashlib

from django.utils.encoding import force_bytes
from django.utils.functional import cached_property

__all__ = ['Index']

# The max length of the names of the indexes (restricted to 30 due to Oracle)
MAX_NAME_LENGTH = 30


class Index(object):
    suffix = 'idx'

    def __init__(self, fields=[], name=None):
        if not fields:
            raise ValueError('At least one field is required to define an index.')
        self.fields = fields
        self._name = name or ''
        if self._name:
            errors = self.check_name()
            if len(self._name) > MAX_NAME_LENGTH:
                errors.append('Index names cannot be longer than %s characters.' % MAX_NAME_LENGTH)
            if errors:
                raise ValueError(errors)

    @cached_property
    def name(self):
        if not self._name:
            self._name = self.get_name()
            self.check_name()
        return self._name

    def check_name(self):
        errors = []
        # Name can't start with an underscore on Oracle; prepend D if needed.
        if self._name[0] == '_':
            errors.append('Index names cannot start with an underscore (_).')
            self._name = 'D%s' % self._name[1:]
        # Name can't start with a number on Oracle; prepend D if needed.
        elif self._name[0].isdigit():
            errors.append('Index names cannot start with a number (0-9).')
            self._name = 'D%s' % self._name[1:]
        return errors

    def create_sql(self, model, schema_editor):
        fields = [model._meta.get_field(field) for field in self.fields]
        tablespace_sql = schema_editor._get_index_tablespace_sql(model, fields)
        columns = [field.column for field in fields]

        quote_name = schema_editor.quote_name
        return schema_editor.sql_create_index % {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
            'columns': ', '.join(quote_name(column) for column in columns),
            'extra': tablespace_sql,
        }

    def remove_sql(self, model, schema_editor):
        quote_name = schema_editor.quote_name
        return schema_editor.sql_delete_index % {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
        }

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace('django.db.models.indexes', 'django.db.models')
        return (path, (), {'fields': self.fields})

    @staticmethod
    def _hash_generator(*args):
        """
        Generate a 32-bit digest of a set of arguments that can be used to
        shorten identifying names.
        """
        h = hashlib.md5()
        for arg in args:
            h.update(force_bytes(arg))
        return h.hexdigest()[:6]

    def get_name(self):
        """
        Generate a unique name for the index.

        The name is divided into 3 parts - table name (12 chars), field name
        (8 chars) and unique hash + suffix (10 chars). Each part is made to
        fit its size by truncating the excess length.
        """
        table_name = self.model._meta.db_table
        column_names = [self.model._meta.get_field(field).column for field in self.fields]
        hash_data = [table_name] + column_names + [self.suffix]
        index_name = '%s_%s_%s' % (
            table_name[:11],
            column_names[0][:7],
            '%s_%s' % (self._hash_generator(*hash_data), self.suffix),
        )
        assert len(index_name) <= 30, (
            'Index too long for multiple database support. Is self.suffix '
            'longer than 3 characters?'
        )
        return index_name

    def __repr__(self):
        return "<%s: fields='%s'>" % (self.__class__.__name__, ', '.join(self.fields))

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.deconstruct() == other.deconstruct())

    def __ne__(self, other):
        return not (self == other)
