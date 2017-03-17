from django.db import connection
from django.db.models import Index
from django.utils.functional import cached_property

__all__ = ['BrinIndex', 'GinIndex']


class BrinIndex(Index):
    suffix = 'brin'

    def __init__(self, fields=[], name=None, pages_per_range=None):
        if pages_per_range is not None and pages_per_range <= 0:
            raise ValueError('pages_per_range must be None or a positive integer')
        self.pages_per_range = pages_per_range
        super().__init__(fields, name)

    def __repr__(self):
        if self.pages_per_range is not None:
            return '<%(name)s: fields=%(fields)s, pages_per_range=%(pages_per_range)s>' % {
                'name': self.__class__.__name__,
                'fields': "'{}'".format(', '.join(self.fields)),
                'pages_per_range': self.pages_per_range,
            }
        else:
            return super().__repr__()

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs['pages_per_range'] = self.pages_per_range
        return path, args, kwargs

    def get_sql_create_template_values(self, model, schema_editor, using):
        parameters = super().get_sql_create_template_values(model, schema_editor, using=' USING brin')
        if self.pages_per_range is not None:
            parameters['extra'] = ' WITH (pages_per_range={})'.format(
                schema_editor.quote_value(self.pages_per_range)) + parameters['extra']
        return parameters

    @cached_property
    def max_name_length(self):
        # Allow an index name longer than 30 characters since the suffix
        # is 4 characters (usual limit is 3). Since this index can only be
        # used on PostgreSQL, the 30 character limit for cross-database
        # compatibility isn't applicable.
        return connection.ops.max_name_length()


class GinIndex(Index):
    suffix = 'gin'

    def create_sql(self, model, schema_editor):
        return super().create_sql(model, schema_editor, using=' USING gin')
