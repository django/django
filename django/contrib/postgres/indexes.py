from django.db.models import Index

__all__ = ['BrinIndex', 'GinIndex']


class BrinIndex(Index):
    suffix = 'brin'
    # Allow an index name longer than 30 characters since the suffix is 4
    # characters (usual limit is 3). Since this index can only be used on
    # PostgreSQL, the 30 character limit for cross-database compatibility isn't
    # applicable.
    max_name_length = 31

    def __init__(self, *, pages_per_range=None, **kwargs):
        if pages_per_range is not None and pages_per_range <= 0:
            raise ValueError('pages_per_range must be None or a positive integer')
        self.pages_per_range = pages_per_range
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs['pages_per_range'] = self.pages_per_range
        return path, args, kwargs

    def create_sql(self, model, schema_editor, using=''):
        statement = super().create_sql(model, schema_editor, using=' USING brin')
        if self.pages_per_range is not None:
            statement.parts['extra'] = ' WITH (pages_per_range={})'.format(
                schema_editor.quote_value(self.pages_per_range)
            ) + statement.parts['extra']
        return statement


class GinIndex(Index):
    suffix = 'gin'

    def __init__(self, *, fastupdate=None, gin_pending_list_limit=None, **kwargs):
        self.fastupdate = fastupdate
        self.gin_pending_list_limit = gin_pending_list_limit
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs['fastupdate'] = self.fastupdate
        kwargs['gin_pending_list_limit'] = self.gin_pending_list_limit
        return path, args, kwargs

    def create_sql(self, model, schema_editor, using=''):
        statement = super().create_sql(model, schema_editor, using=' USING gin')
        with_params = []
        if self.gin_pending_list_limit is not None:
            with_params.append('gin_pending_list_limit = %d' % self.gin_pending_list_limit)
        if self.fastupdate is not None:
            with_params.append('fastupdate = {}'.format('on' if self.fastupdate else 'off'))
        if with_params:
            statement.parts['extra'] = 'WITH ({}) {}'.format(', '.join(with_params), statement.parts['extra'])
        return statement
