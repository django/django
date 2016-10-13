from __future__ import unicode_literals

import hashlib

from django.utils.encoding import force_bytes

__all__ = [str('Index')]

# The max length of the names of the indexes (restricted to 30 due to Oracle)
MAX_NAME_LENGTH = 30


class Index(object):
    suffix = 'idx'

    def __init__(self, fields=[], name=None):
        if not isinstance(fields, list):
            raise ValueError('Index.fields must be a list.')
        if not fields:
            raise ValueError('At least one field is required to define an index.')
        self.fields = fields
        # A list of 2-tuple with the field name and ordering ('' or 'DESC').
        self.fields_orders = [
            (field_name[1:], 'DESC') if field_name.startswith('-') else (field_name, '')
            for field_name in self.fields
        ]
        self.name = name or ''
        if self.name:
            errors = self.check_name()
            if len(self.name) > MAX_NAME_LENGTH:
                errors.append('Index names cannot be longer than %s characters.' % MAX_NAME_LENGTH)
            if errors:
                raise ValueError(errors)

    def check_name(self):
        errors = []
        # Name can't start with an underscore on Oracle; prepend D if needed.
        if self.name[0] == '_':
            errors.append('Index names cannot start with an underscore (_).')
            self.name = 'D%s' % self.name[1:]
        # Name can't start with a number on Oracle; prepend D if needed.
        elif self.name[0].isdigit():
            errors.append('Index names cannot start with a number (0-9).')
            self.name = 'D%s' % self.name[1:]
        return errors

    def get_sql_create_template_values(self, model, schema_editor, using):
        fields = [model._meta.get_field(field_name) for field_name, order in self.fields_orders]
        tablespace_sql = schema_editor._get_index_tablespace_sql(model, fields)
        quote_name = schema_editor.quote_name
        columns = [
            ('%s %s' % (quote_name(field.column), order)).strip()
            for field, (field_name, order) in zip(fields, self.fields_orders)
        ]
        return {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
            'columns': ', '.join(columns),
            'using': using,
            'extra': tablespace_sql,
        }

    def create_sql(self, model, schema_editor, using='', parameters=None):
        sql_create_index = schema_editor.sql_create_index
        sql_parameters = parameters or self.get_sql_create_template_values(model, schema_editor, using)
        return sql_create_index % sql_parameters

    def remove_sql(self, model, schema_editor):
        quote_name = schema_editor.quote_name
        return schema_editor.sql_delete_index % {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
        }

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace('django.db.models.indexes', 'django.db.models')
        return (path, (), {'fields': self.fields, 'name': self.name})

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

    def set_name_with_model(self, model):
        """
        Generate a unique name for the index.

        The name is divided into 3 parts - table name (12 chars), field name
        (8 chars) and unique hash + suffix (10 chars). Each part is made to
        fit its size by truncating the excess length.
        """
        table_name = model._meta.db_table
        column_names = [model._meta.get_field(field_name).column for field_name, order in self.fields_orders]
        column_names_with_order = [
            (('-%s' if order else '%s') % column_name)
            for column_name, (field_name, order) in zip(column_names, self.fields_orders)
        ]
        hash_data = [table_name] + column_names_with_order + [self.suffix]
        self.name = '%s_%s_%s' % (
            table_name[:11],
            column_names[0][:7],
            '%s_%s' % (self._hash_generator(*hash_data), self.suffix),
        )
        assert len(self.name) <= 30, (
            'Index too long for multiple database support. Is self.suffix '
            'longer than 3 characters?'
        )
        self.check_name()

    def __repr__(self):
        return "<%s: fields='%s'>" % (self.__class__.__name__, ', '.join(self.fields))

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.deconstruct() == other.deconstruct())

    def __ne__(self, other):
        return not (self == other)
