import hashlib

from django.db.backends.utils import split_identifier
from django.utils.encoding import force_bytes

__all__ = ['Index']


class Index:
    suffix = 'idx'
    # The max length of the name of the index (restricted to 30 for
    # cross-database compatibility with Oracle)
    max_name_length = 30

    def __init__(self, *, fields=[], name=None, db_tablespace=None):
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
            if len(self.name) > self.max_name_length:
                errors.append('Index names cannot be longer than %s characters.' % self.max_name_length)
            if errors:
                raise ValueError(errors)
        self.db_tablespace = db_tablespace

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

    def create_sql(self, model, schema_editor, using=''):
        fields = [model._meta.get_field(field_name) for field_name, _ in self.fields_orders]
        col_suffixes = [order[1] for order in self.fields_orders]
        return schema_editor._create_index_sql(
            model, fields, name=self.name, using=using, db_tablespace=self.db_tablespace,
            col_suffixes=col_suffixes,
        )

    def remove_sql(self, model, schema_editor):
        quote_name = schema_editor.quote_name
        return schema_editor.sql_delete_index % {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
        }

    def deconstruct(self):
        path = '%s.%s' % (self.__class__.__module__, self.__class__.__name__)
        path = path.replace('django.db.models.indexes', 'django.db.models')
        kwargs = {'fields': self.fields, 'name': self.name}
        if self.db_tablespace is not None:
            kwargs['db_tablespace'] = self.db_tablespace
        return (path, (), kwargs)

    def clone(self):
        """Create a copy of this Index."""
        path, args, kwargs = self.deconstruct()
        return self.__class__(*args, **kwargs)

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
        _, table_name = split_identifier(model._meta.db_table)
        column_names = [model._meta.get_field(field_name).column for field_name, order in self.fields_orders]
        column_names_with_order = [
            (('-%s' if order else '%s') % column_name)
            for column_name, (field_name, order) in zip(column_names, self.fields_orders)
        ]
        # The length of the parts of the name is based on the default max
        # length of 30 characters.
        hash_data = [table_name] + column_names_with_order + [self.suffix]
        self.name = '%s_%s_%s' % (
            table_name[:11],
            column_names[0][:7],
            '%s_%s' % (self._hash_generator(*hash_data), self.suffix),
        )
        assert len(self.name) <= self.max_name_length, (
            'Index too long for multiple database support. Is self.suffix '
            'longer than 3 characters?'
        )
        self.check_name()

    def __repr__(self):
        return "<%s: fields='%s'>" % (self.__class__.__name__, ', '.join(self.fields))

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.deconstruct() == other.deconstruct())
