import hashlib

from django.db.models import F
from django.db.models.expressions import Expression
from django.db.models.sql.query import ExpressionIndexQuery
from django.utils.encoding import force_bytes

__all__ = ['Index']


class ExpressionIndexNotSupported(ValueError):
    pass


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
        self.fields_names = [field_name.lstrip('-') for field_name in self.fields if isinstance(field_name, str)]
        self.expressions = []
        for field in self.fields:
            if isinstance(field, str):
                expression = F(field[1:]).desc() if field.startswith('-') else F(field)
                self.expressions.append(expression)
            else:
                self.expressions.append(field)

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

    def get_sql_create_template_values(self, model, schema_editor, using):
        connection = schema_editor.connection
        query = ExpressionIndexQuery(model)
        compiler = connection.ops.compiler('SQLCompiler')(query, connection, 'default')

        columns = []
        supports_expression_indexes = connection.features.supports_expression_indexes
        for column_expression in self.expressions:
            if (not supports_expression_indexes and
                    hasattr(column_expression, 'flatten') and
                    any(isinstance(expr, Expression) for expr in column_expression.flatten())):
                raise ExpressionIndexNotSupported(
                    (
                        'Not creating expression index:\n'
                        '   {expression}\n'
                        'Expression indexes are not supported on {vendor}.'
                    ).format(expression=column_expression, vendor=connection.display_name),
                )

            expression = column_expression.resolve_expression(query)
            column_sql, params = compiler.compile(expression)
            params = tuple(map(schema_editor.quote_value, params))
            columns.append(column_sql % params)

        fields_for_tablespace = [model._meta.get_field(field_name) for field_name in self.fields_names]
        tablespace_sql = schema_editor._get_index_tablespace_sql(model, fields_for_tablespace, self.db_tablespace)

        quote_name = schema_editor.quote_name

        return {
            'table': quote_name(model._meta.db_table),
            'name': quote_name(self.name),
            'columns': ', '.join(columns),
            'using': using,
            'extra': tablespace_sql,
        }

    def create_sql(self, model, schema_editor, using=''):
        sql_create_index = schema_editor.sql_create_index
        sql_parameters = self.get_sql_create_template_values(model, schema_editor, using)
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
        table_name = model._meta.db_table
        column_names = [model._meta.get_field(field_name).column for field_name in self.fields_names]
        column_names_with_order = [
            (('-%s' if field_name.startswith('-') else '%s') % column_name)
            for column_name, field_name in zip(column_names, self.fields)
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
        return "<%s: fields='%s'>" % (self.__class__.__name__, ', '.join(map(str, self.fields)))

    def __eq__(self, other):
        return (self.__class__ == other.__class__) and (self.deconstruct() == other.deconstruct())
