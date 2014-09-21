import hashlib

from django.db.backends.utils import truncate_name
from django.utils.encoding import force_bytes


__all__ = ['Index']


class Index(object):
    def __init__(self, fields=None, field_names=None, model=None):
        self.fields = fields
        self.field_names = tuple(field_names) if field_names else ()
        self.model = model
        if self.fields:
            self.field_names = tuple(f.name for f in fields)

    def _normalize_fields(self):
        if self.fields is None:
            self.fields = [self.model._meta.get_field_by_name(field)[0] for field in self.field_names]
        if self.model is None:
            self.model = self.fields[0].model

    def get_name(self, schema, suffix=''):
        # If there is just one column, use the old algorithm
        column_names = [field.column for field in self.fields]
        if len(column_names) == 1 and not suffix:
            from django.db.backends.creation import BaseDatabaseCreation
            return truncate_name(
                '%s_%s' % (self.model._meta.db_table, BaseDatabaseCreation._digest(column_names[0])),
                schema.connection.ops.max_name_length()
            )
        # Else generate the name for the index using a different algorithm
        table_name = self.model._meta.db_table.replace('"', '').replace('.', '_')
        index_unique_name = '_%x' % abs(hash((table_name, ','.join(column_names))))
        max_length = schema.connection.ops.max_name_length() or 200
        # If the index name is too long, truncate it
        index_name = ('%s_%s%s%s' % (
            table_name, column_names[0], index_unique_name, suffix,
        )).replace('"', '').replace('.', '_')
        if len(index_name) > max_length:
            part = ('_%s%s%s' % (column_names[0], index_unique_name, suffix))
            index_name = '%s%s' % (table_name[:(max_length - len(part))], part)
        # It shouldn't start with an underscore (Oracle hates this)
        if index_name[0] == "_":
            index_name = index_name[1:]
        # If it's STILL too long, just hash it down
        if len(index_name) > max_length:
            index_name = hashlib.md5(force_bytes(index_name)).hexdigest()[:max_length]
        # It can't start with a number on Oracle, so prepend D if we need to
        if index_name[0].isdigit():
            index_name = "D%s" % index_name[:-1]
        return index_name

    def as_sql(self, schema, suffix=''):
        self._normalize_fields()
        columns = [field.column for field in self.fields]
        return schema.sql_create_index % {
            "table": schema.quote_name(self.model._meta.db_table),
            "name": self.get_name(schema=schema, suffix=suffix),
            "columns": ", ".join(schema.quote_name(column) for column in columns),
            "extra": "",
        }

    def as_remove_sql(self, schema, suffix=''):
        self._normalize_fields()
        return schema.sql_delete_index % {
            "name": self.get_name(schema=schema, suffix=suffix),
        }

    def deconstruct(self):
        """
        Returns a 3-tuple of class import path, positional arguments, and keyword
        arguments.
        """
        kwargs = {'field_names': self.field_names}
        return (self.__class__.__name__, (), kwargs)

    def __repr__(self):
        return "<%s: fields=%s>" % (
            self.__class__.__name__,
            ','.join(self.field_names),
        )

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.deconstruct() == other.deconstruct())

    def __ne__(self, other):
        return not (self == other)
