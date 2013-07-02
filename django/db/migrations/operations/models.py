from .base import Operation
from django.db import models
from django.db.migrations.state import ModelState


class CreateModel(Operation):
    """
    Create a model's table.
    """

    def __init__(self, name, fields, options=None, bases=None):
        self.name = name.lower()
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
        self.name = name.lower()

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


class AlterModelTable(Operation):
    """
    Renames a model's table
    """

    def __init__(self, name, table):
        self.name = name.lower()
        self.table = table

    def state_forwards(self, app_label, state):
        state.models[app_label, self.name.lower()].options["db_table"] = self.table

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_app_cache = from_state.render()
        new_app_cache = to_state.render()
        schema_editor.alter_db_table(
            new_app_cache.get_model(app_label, self.name),
            old_app_cache.get_model(app_label, self.name)._meta.db_table,
            new_app_cache.get_model(app_label, self.name)._meta.db_table,
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Rename table for %s to %s" % (self.name, self.table)


class AlterUniqueTogether(Operation):
    """
    Changes the value of index_together to the target one.
    Input value of unique_together must be a set of tuples.
    """

    def __init__(self, name, unique_together):
        self.name = name.lower()
        self.unique_together = set(tuple(cons) for cons in unique_together)

    def state_forwards(self, app_label, state):
        model_state = state.models[app_label, self.name.lower()]
        model_state.options["unique_together"] = self.unique_together

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_app_cache = from_state.render()
        new_app_cache = to_state.render()
        schema_editor.alter_unique_together(
            new_app_cache.get_model(app_label, self.name),
            getattr(old_app_cache.get_model(app_label, self.name)._meta, "unique_together", set()),
            getattr(new_app_cache.get_model(app_label, self.name)._meta, "unique_together", set()),
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Alter unique_together for %s (%s constraints)" % (self.name, len(self.unique_together))


class AlterIndexTogether(Operation):
    """
    Changes the value of index_together to the target one.
    Input value of index_together must be a set of tuples.
    """

    def __init__(self, name, index_together):
        self.name = name.lower()
        self.index_together = set(tuple(cons) for cons in index_together)

    def state_forwards(self, app_label, state):
        model_state = state.models[app_label, self.name.lower()]
        model_state.options["index_together"] = self.index_together

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_app_cache = from_state.render()
        new_app_cache = to_state.render()
        schema_editor.alter_index_together(
            new_app_cache.get_model(app_label, self.name),
            getattr(old_app_cache.get_model(app_label, self.name)._meta, "index_together", set()),
            getattr(new_app_cache.get_model(app_label, self.name)._meta, "index_together", set()),
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Alter index_together for %s (%s constraints)" % (self.name, len(self.index_together))
