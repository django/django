from .base import Operation
from django.db.migrations.state import ModelState


class CreateModel(Operation):
    """
    Create a model's table.
    """

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app, state):
        state.models[app, self.name.lower()] = ModelState(state, app, self.name)

    def database_forwards(self, app, schema_editor, from_state, to_state):
        app_cache = to_state.render()
        schema_editor.create_model(app_cache.get_model(app, self.name))

    def database_backwards(self, app, schema_editor, from_state, to_state):
        """
        Performs the mutation on the database schema in the reverse
        direction - e.g. if this were CreateModel, it would in fact
        drop the model's table.
        """
        raise NotImplementedError()
