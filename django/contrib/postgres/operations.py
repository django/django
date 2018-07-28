from django.contrib.postgres.signals import (
    get_citext_oids, get_hstore_oids, register_type_handlers,
)
from django.db.migrations.operations.base import Operation


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
