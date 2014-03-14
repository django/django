from django.db import models, router
from django.db.models.options import normalize_together
from django.db.migrations.state import ModelState
from django.db.migrations.operations.base import Operation
from django.utils import six


class CreateModel(Operation):
    """
    Create a model's table.
    """

    serialization_expand_args = ['fields', 'options']

    def __init__(self, name, fields, options=None, bases=None):
        self.name = name
        self.fields = fields
        self.options = options or {}
        self.bases = bases or (models.Model,)

    def state_forwards(self, app_label, state):
        state.models[app_label, self.name.lower()] = ModelState(app_label, self.name, self.fields, self.options, self.bases)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        apps = to_state.render()
        model = apps.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        apps = from_state.render()
        model = apps.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    def describe(self):
        return "Create model %s" % (self.name, )

    def references_model(self, name, app_label=None):
        strings_to_check = [self.name]
        # Check we didn't inherit from the model
        for base in self.bases:
            if isinstance(base, six.string_types):
                strings_to_check.append(base.split(".")[-1])
        # Check we have no FKs/M2Ms with it
        for fname, field in self.fields:
            if field.rel:
                if isinstance(field.rel.to, six.string_types):
                    strings_to_check.append(field.rel.to.split(".")[-1])
        # Now go over all the strings and compare them
        for string in strings_to_check:
            if string.lower() == name.lower():
                return True
        return False

    def __eq__(self, other):
        return (
            (self.__class__ == other.__class__) and
            (self.name == other.name) and
            (self.options == other.options) and
            (self.bases == other.bases) and
            ([(k, f.deconstruct()[1:]) for k, f in self.fields] == [(k, f.deconstruct()[1:]) for k, f in other.fields])
        )


class DeleteModel(Operation):
    """
    Drops a model's table.
    """

    def __init__(self, name):
        self.name = name

    def state_forwards(self, app_label, state):
        del state.models[app_label, self.name.lower()]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        apps = from_state.render()
        model = apps.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        apps = to_state.render()
        model = apps.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    def references_model(self, name, app_label=None):
        return name.lower() == self.name.lower()

    def describe(self):
        return "Delete model %s" % (self.name, )


class RenameModel(Operation):
    """
    Renames a model.
    """

    def __init__(self, old_name, new_name):
        self.old_name = old_name
        self.new_name = new_name

    def state_forwards(self, app_label, state):
        state.models[app_label, self.new_name.lower()] = state.models[app_label, self.old_name.lower()]
        state.models[app_label, self.new_name.lower()].name = self.new_name
        del state.models[app_label, self.old_name.lower()]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_apps = from_state.render()
        new_apps = to_state.render()
        old_model = old_apps.get_model(app_label, self.old_name)
        new_model = new_apps.get_model(app_label, self.new_name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        old_apps = from_state.render()
        new_apps = to_state.render()
        old_model = old_apps.get_model(app_label, self.new_name)
        new_model = new_apps.get_model(app_label, self.old_name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )

    def references_model(self, name, app_label=None):
        return (
            name.lower() == self.old_name.lower() or
            name.lower() == self.new_name.lower()
        )

    def describe(self):
        return "Rename model %s to %s" % (self.old_name, self.new_name)


class AlterModelTable(Operation):
    """
    Renames a model's table
    """

    def __init__(self, name, table):
        self.name = name
        self.table = table

    def state_forwards(self, app_label, state):
        state.models[app_label, self.name.lower()].options["db_table"] = self.table

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_apps = from_state.render()
        new_apps = to_state.render()
        old_model = old_apps.get_model(app_label, self.name)
        new_model = new_apps.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def references_model(self, name, app_label=None):
        return name.lower() == self.name.lower()

    def describe(self):
        return "Rename table for %s to %s" % (self.name, self.table)


class AlterUniqueTogether(Operation):
    """
    Changes the value of index_together to the target one.
    Input value of unique_together must be a set of tuples.
    """

    def __init__(self, name, unique_together):
        self.name = name
        unique_together = normalize_together(unique_together)
        self.unique_together = set(tuple(cons) for cons in unique_together)

    def state_forwards(self, app_label, state):
        model_state = state.models[app_label, self.name.lower()]
        model_state.options["unique_together"] = self.unique_together

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_apps = from_state.render()
        new_apps = to_state.render()
        old_model = old_apps.get_model(app_label, self.name)
        new_model = new_apps.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_unique_together(
                new_model,
                getattr(old_model._meta, "unique_together", set()),
                getattr(new_model._meta, "unique_together", set()),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def references_model(self, name, app_label=None):
        return name.lower() == self.name.lower()

    def describe(self):
        return "Alter unique_together for %s (%s constraints)" % (self.name, len(self.unique_together))


class AlterIndexTogether(Operation):
    """
    Changes the value of index_together to the target one.
    Input value of index_together must be a set of tuples.
    """

    def __init__(self, name, index_together):
        self.name = name
        index_together = normalize_together(index_together)
        self.index_together = set(tuple(cons) for cons in index_together)

    def state_forwards(self, app_label, state):
        model_state = state.models[app_label, self.name.lower()]
        model_state.options["index_together"] = self.index_together

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        old_apps = from_state.render()
        new_apps = to_state.render()
        old_model = old_apps.get_model(app_label, self.name)
        new_model = new_apps.get_model(app_label, self.name)
        if router.allow_migrate(schema_editor.connection.alias, new_model):
            schema_editor.alter_index_together(
                new_model,
                getattr(old_model._meta, "index_together", set()),
                getattr(new_model._meta, "index_together", set()),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def references_model(self, name, app_label=None):
        return name.lower() == self.name.lower()

    def describe(self):
        return "Alter index_together for %s (%s constraints)" % (self.name, len(self.index_together))
