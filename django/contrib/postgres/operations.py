import re

from django.contrib.postgres.signals import (
    get_citext_oids, get_hstore_oids, register_type_handlers,
)
from django.db.migrations import AddIndex, RemoveIndex
from django.db.migrations.operations.base import Operation
from django.db.utils import NotSupportedError


class CreateExtension(Operation):
    reversible = True

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor != 'postgresql':
            return
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS %s" % schema_editor.quote_name(self.name))
        # Clear cached, stale oids.
        get_hstore_oids.cache_clear()
        get_citext_oids.cache_clear()
        # Registering new type handlers cannot be done before the extension is
        # installed, otherwise a subsequent data migration would use the same
        # connection.
        register_type_handlers(schema_editor.connection)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute("DROP EXTENSION %s" % schema_editor.quote_name(self.name))
        # Clear cached, stale oids.
        get_hstore_oids.cache_clear()
        get_citext_oids.cache_clear()

    def describe(self):
        return "Creates extension %s" % self.name


class BtreeGinExtension(CreateExtension):

    def __init__(self):
        self.name = 'btree_gin'


class BtreeGistExtension(CreateExtension):

    def __init__(self):
        self.name = 'btree_gist'


class CITextExtension(CreateExtension):

    def __init__(self):
        self.name = 'citext'


class CryptoExtension(CreateExtension):

    def __init__(self):
        self.name = 'pgcrypto'


class HStoreExtension(CreateExtension):

    def __init__(self):
        self.name = 'hstore'


class TrigramExtension(CreateExtension):

    def __init__(self):
        self.name = 'pg_trgm'


class UnaccentExtension(CreateExtension):

    def __init__(self):
        self.name = 'unaccent'


class AddIndexConcurrently(AddIndex):
    """Create an index using Postgres's CREATE INDEX CONCURRENTLY syntax."""

    def describe(self):
        return re.sub(r'^Create', 'Concurrently create', super().describe())

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)

        model = to_state.apps.get_model(app_label, self.model_name)
        sql = re.sub('^CREATE INDEX', 'CREATE INDEX CONCURRENTLY', str(self.index.create_sql(model, schema_editor)))
        schema_editor.execute(sql)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)

        model = from_state.apps.get_model(app_label, self.model_name)
        sql = re.sub('^DROP INDEX', 'DROP INDEX CONCURRENTLY', str(self.index.remove_sql(model, schema_editor)))
        schema_editor.execute(sql)

    def _ensure_not_in_transaction(self, schema_editor):
        if schema_editor.connection.in_atomic_block:
            raise NotSupportedError(
                'The %s operation cannot be executed inside a transaction '
                '(set atomic = False on the migration).' % self.__class__.__name__
            )


class RemoveIndexConcurrently(RemoveIndex):
    """Delete an index using Postgres's DROP INDEX CONCURRENTLY syntax."""

    def describe(self):
        return re.sub(r'^Remove', 'Concurrently remove', super().describe())

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)

        model = from_state.apps.get_model(app_label, self.model_name)
        from_model_state = from_state.models[app_label, self.model_name_lower]
        index = from_model_state.get_index_by_name(self.name)
        sql = re.sub('^DROP INDEX', 'DROP INDEX CONCURRENTLY', str(index.remove_sql(model, schema_editor)))
        schema_editor.execute(sql)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self._ensure_not_in_transaction(schema_editor)

        model = to_state.apps.get_model(app_label, self.model_name)
        to_model_state = to_state.models[app_label, self.model_name_lower]
        index = to_model_state.get_index_by_name(self.name)
        sql = re.sub('^CREATE INDEX', 'CREATE INDEX CONCURRENTLY', str(index.create_sql(model, schema_editor)))
        schema_editor.execute(sql)

    def _ensure_not_in_transaction(self, schema_editor):
        if schema_editor.connection.in_atomic_block:
            raise NotSupportedError(
                'The %s operation cannot be executed inside a transaction '
                '(set atomic = False on the migration).' % self.__class__.__name__
            )
