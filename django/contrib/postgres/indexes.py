from django.db.models import Index
from django.db.utils import NotSupportedError
from django.utils.functional import cached_property

__all__ = [
    'BrinIndex', 'BTreeIndex', 'GinIndex', 'GistIndex', 'HashIndex',
    'SpGistIndex',
]


class PostgresIndex(Index):

    @cached_property
    def max_name_length(self):
        # Allow an index name longer than 30 characters when the suffix is
        # longer than the usual 3 character limit. The 30 character limit for
        # cross-database compatibility isn't applicable to PostgreSQL-specific
        # indexes.
        return Index.max_name_length - len(Index.suffix) + len(self.suffix)

    def create_sql(self, model, schema_editor, using='', **kwargs):
        self.check_supported(schema_editor)
        statement = super().create_sql(model, schema_editor, using=' USING %s' % self.suffix, **kwargs)
        with_params = self.get_with_params()
        if with_params:
            statement.parts['extra'] = 'WITH (%s) %s' % (
                ', '.join(with_params),
                statement.parts['extra'],
            )
        return statement

    def check_supported(self, schema_editor):
        pass

    def get_with_params(self):
        return []


class BrinIndex(PostgresIndex):
    suffix = 'brin'

    def __init__(self, *, autosummarize=None, pages_per_range=None, **kwargs):
        if pages_per_range is not None and pages_per_range <= 0:
            raise ValueError('pages_per_range must be None or a positive integer')
        self.autosummarize = autosummarize
        self.pages_per_range = pages_per_range
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.autosummarize is not None:
            kwargs['autosummarize'] = self.autosummarize
        if self.pages_per_range is not None:
            kwargs['pages_per_range'] = self.pages_per_range
        return path, args, kwargs

    def check_supported(self, schema_editor):
        if self.autosummarize and not schema_editor.connection.features.has_brin_autosummarize:
            raise NotSupportedError('BRIN option autosummarize requires PostgreSQL 10+.')

    def get_with_params(self):
        with_params = []
        if self.autosummarize is not None:
            with_params.append('autosummarize = %s' % ('on' if self.autosummarize else 'off'))
        if self.pages_per_range is not None:
            with_params.append('pages_per_range = %d' % self.pages_per_range)
        return with_params


class BTreeIndex(PostgresIndex):
    suffix = 'btree'

    def __init__(self, *, fillfactor=None, **kwargs):
        self.fillfactor = fillfactor
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.fillfactor is not None:
            kwargs['fillfactor'] = self.fillfactor
        return path, args, kwargs

    def get_with_params(self):
        with_params = []
        if self.fillfactor is not None:
            with_params.append('fillfactor = %d' % self.fillfactor)
        return with_params


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

    def get_with_params(self):
        with_params = []
        if self.gin_pending_list_limit is not None:
            with_params.append('gin_pending_list_limit = %d' % self.gin_pending_list_limit)
        if self.fastupdate is not None:
            with_params.append('fastupdate = %s' % ('on' if self.fastupdate else 'off'))
        return with_params


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

    def get_with_params(self):
        with_params = []
        if self.buffering is not None:
            with_params.append('buffering = %s' % ('on' if self.buffering else 'off'))
        if self.fillfactor is not None:
            with_params.append('fillfactor = %d' % self.fillfactor)
        return with_params


class HashIndex(PostgresIndex):
    suffix = 'hash'

    def __init__(self, *, fillfactor=None, **kwargs):
        self.fillfactor = fillfactor
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.fillfactor is not None:
            kwargs['fillfactor'] = self.fillfactor
        return path, args, kwargs

    def get_with_params(self):
        with_params = []
        if self.fillfactor is not None:
            with_params.append('fillfactor = %d' % self.fillfactor)
        return with_params


class SpGistIndex(PostgresIndex):
    suffix = 'spgist'

    def __init__(self, *, fillfactor=None, **kwargs):
        self.fillfactor = fillfactor
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.fillfactor is not None:
            kwargs['fillfactor'] = self.fillfactor
        return path, args, kwargs

    def get_with_params(self):
        with_params = []
        if self.fillfactor is not None:
            with_params.append('fillfactor = %d' % self.fillfactor)
        return with_params
