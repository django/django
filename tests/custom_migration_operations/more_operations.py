from django.db.migrations.operations.base import Operation


class TestOperation(Operation):
    def __init__(self):
        pass

    def deconstruct(self):
        return (
            self.__class__.__name__,
            [],
            {}
        )

    @property
    def reversible(self):
        return True

    def state_forwards(self, app_label, state):
        pass

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def state_backwards(self, app_label, state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass
