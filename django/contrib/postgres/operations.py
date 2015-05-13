from django.contrib.postgres.signals import register_hstore_handler
from django.db.backends.postgresql.migrations.operations import CreateExtension


class HStoreExtension(CreateExtension):

    def __init__(self):
        self.name = 'hstore'

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        super(HStoreExtension, self).database_forwards(app_label, schema_editor, from_state, to_state)
        # Register hstore straight away as it cannot be done before the
        # extension is installed, a subsequent data migration would use the
        # same connection
        register_hstore_handler(schema_editor.connection)


class UnaccentExtension(CreateExtension):

    def __init__(self):
        self.name = 'unaccent'


class TrigramExtension(CreateExtension):

    def __init__(self):
        self.name = 'pg_trgm'


class BtreeGinExtension(CreateExtension):

    def __init__(self):
        self.name = 'btree_gin'
