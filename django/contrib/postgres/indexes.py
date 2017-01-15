from __future__ import unicode_literals

from django.db.models import Index

__all__ = ['BrinIndex', 'GinIndex']


class BrinIndex(Index):
    suffix = 'brin'

    def __init__(self, fields=[], name=None, pages_per_range=None):
        if pages_per_range is not None and not (isinstance(pages_per_range, int) and pages_per_range > 0):
            raise ValueError('pages_per_range must be None or a positive integer for BRIN indexes')
        self.pages_per_range = pages_per_range
        return super(BrinIndex, self).__init__(fields, name)

    def __repr__(self):
        if self.pages_per_range is not None:
            return '<%(name)s: fields=%(fields)s, pages_per_range=%(pages_per_range)s>' % {
                'name': self.__class__.__name__,
                'fields': "'{}'".format(', '.join(self.fields)),
                'pages_per_range': self.pages_per_range,
            }
        else:
            return super(BrinIndex, self).__repr__()

    def deconstruct(self):
        path, args, kwargs = super(BrinIndex, self).deconstruct()
        kwargs['pages_per_range'] = self.pages_per_range
        return path, args, kwargs

    def get_sql_create_template_values(self, model, schema_editor, using):
        parameters = super(BrinIndex, self).get_sql_create_template_values(model, schema_editor, using=' USING brin')
        if self.pages_per_range is not None:
            parameters['extra'] = ' WITH (pages_per_range={})'.format(
                schema_editor.quote_value(self.pages_per_range)) + parameters['extra']
        return parameters


class GinIndex(Index):
    suffix = 'gin'

    def create_sql(self, model, schema_editor):
        return super(GinIndex, self).create_sql(model, schema_editor, using=' USING gin')
