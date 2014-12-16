from django.contrib.postgres.signals import register_hstore_handler
from django.db.migrations.operations.base import Operation


class CreateExtension(Operation):
    reversible = True

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS %s" % self.name)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute("DROP EXTENSION %s" % self.name)

    def describe(self):
        return "Creates extension %s" % self.name


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
