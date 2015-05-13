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

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        schema_editor.execute("DROP EXTENSION %s" % schema_editor.quote_name(self.name))

    def describe(self):
        return "Creates extension %s" % self.name
