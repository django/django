from __future__ import unicode_literals

from django.db.models import Index

__all__ = ['GinIndex']


class GinIndex(Index):
    suffix = 'gin'

    def create_sql(self, model, schema_editor):
        if schema_editor.connection.vendor == 'postgresql':
            using = ' USING gin'
            return super(GinIndex, self).create_sql(model, schema_editor, using)
        # Raise error for other databases?
