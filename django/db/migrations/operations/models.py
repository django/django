from .base import Operation
from django.db import models
from django.db.migrations.state import ModelState


class CreateModel(Operation):
    """
    Create a model's table.
    """

    def __init__(self, name, fields, options=None, bases=None):
        self.name = name
        self.fields = fields
        self.options = options or {}
        self.bases = bases or (models.Model,)

    def state_forwards(self, app_label, state):
        state.models[app_label, self.name.lower()] = ModelState(app_label, self.name, self.fields, self.options, self.bases)

    def database_forwards(self, app, schema_editor, from_state, to_state):
        app_cache = to_state.render()
        schema_editor.create_model(app_cache.get_model(app, self.name))

    def database_backwards(self, app, schema_editor, from_state, to_state):
        app_cache = from_state.render()
        schema_editor.delete_model(app_cache.get_model(app, self.name))

    def describe(self):
        return "Create model %s" % (self.name, )


class DeleteModel(Operation):
    """
    Drops a model's table.
    """

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app_label, state):
        del state.models[app_label, self.name.lower()]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = from_state.render()
        schema_editor.delete_model(app_cache.get_model(app_label, self.name))

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = to_state.render()
        schema_editor.create_model(app_cache.get_model(app_label, self.name))

    def describe(self):
        return "Delete model %s" % (self.name, )
