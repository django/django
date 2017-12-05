from django.db.models import Index
from django.utils.functional import cached_property

__all__ = ['BrinIndex', 'GinIndex', 'GistIndex']


class PostgresIndex(Index):

    @cached_property
    def max_name_length(self):
        # Allow an index name longer than 30 characters when the suffix is
        # longer than the usual 3 character limit. The 30 character limit for
        # cross-database compatibility isn't applicable to PostgreSQL-specific
        # indexes.
        return Index.max_name_length - len(Index.suffix) + len(self.suffix)


class BrinIndex(PostgresIndex):
    suffix = 'brin'

    def __init__(self, *, pages_per_range=None, **kwargs):
        if pages_per_range is not None and pages_per_range <= 0:
            raise ValueError('pages_per_range must be None or a positive integer')
        self.pages_per_range = pages_per_range
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.pages_per_range is not None:
            kwargs['pages_per_range'] = self.pages_per_range
        return path, args, kwargs

    def create_sql(self, model, schema_editor, using=''):
        statement = super().create_sql(model, schema_editor, using=' USING brin')
        if self.pages_per_range is not None:
            statement.parts['extra'] = ' WITH (pages_per_range={})'.format(
                schema_editor.quote_value(self.pages_per_range)
            ) + statement.parts['extra']
        return statement


class GinIndex(PostgresIndex):
    suffix = 'gin'

    def __init__(self, *, fastupdate=None, gin_pending_list_limit=None, **kwargs):
        self.fastupdate = fastupdate
        self.gin_pending_list_limit = gin_pending_list_limit
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.fastupdate is not None:
            kwargs['fastupdate'] = self.fastupdate
        if self.gin_pending_list_limit is not None:
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


class GistIndex(PostgresIndex):
    suffix = 'gist'

    def __init__(self, *, buffering=None, fillfactor=None, **kwargs):
        self.buffering = buffering
        self.fillfactor = fillfactor
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.buffering is not None:
            kwargs['buffering'] = self.buffering
        if self.fillfactor is not None:
            kwargs['fillfactor'] = self.fillfactor
        return path, args, kwargs

    def create_sql(self, model, schema_editor):
        statement = super().create_sql(model, schema_editor, using=' USING gist')
        with_params = []
        if self.buffering is not None:
            with_params.append('buffering = {}'.format('on' if self.buffering else 'off'))
        if self.fillfactor is not None:
            with_params.append('fillfactor = %s' % self.fillfactor)
        if with_params:
            statement.parts['extra'] = 'WITH ({}) {}'.format(', '.join(with_params), statement.parts['extra'])
        return statement
