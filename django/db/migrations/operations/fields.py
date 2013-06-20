from .base import Operation


class AddField(Operation):
    """
    Adds a field to a model.
    """

    def __init__(self, model_name, name, field):
        self.model_name = model_name
        self.name = name
        self.field = field

    def state_forwards(self, app_label, state):
        state.models[app_label, self.model_name.lower()].fields.append((self.name, self.field))

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.render().get_model(app_label, self.model_name)
        to_model = to_state.render().get_model(app_label, self.model_name)
        schema_editor.add_field(from_model, to_model._meta.get_field_by_name(self.name)[0])

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.render().get_model(app_label, self.model_name)
        schema_editor.remove_field(from_model, from_model._meta.get_field_by_name(self.name)[0])

    def describe(self):
        return "Add field %s to %s" % (self.name, self.model_name)


class RemoveField(Operation):
    """
    Removes a field from a model.
    """

    def __init__(self, model_name, name):
        self.model_name = model_name
        self.name = name

    def state_forwards(self, app_label, state):
        new_fields = []
        for name, instance in state.models[app_label, self.model_name.lower()].fields:
            if name != self.name:
                new_fields.append((name, instance))
        state.models[app_label, self.model_name.lower()].fields = new_fields

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.render().get_model(app_label, self.model_name)
        schema_editor.remove_field(from_model, from_model._meta.get_field_by_name(self.name)[0])

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.render().get_model(app_label, self.model_name)
        to_model = to_state.render().get_model(app_label, self.model_name)
        schema_editor.add_field(from_model, to_model._meta.get_field_by_name(self.name)[0])

    def describe(self):
        return "Remove field %s from %s" % (self.name, self.model_name)


class AlterField(Operation):
    """
    Alters a field's database column (e.g. null, max_length) to the provided new field
    """

    def __init__(self, model_name, name, field):
        self.model_name = model_name
        self.name = name
        self.field = field

    def state_forwards(self, app_label, state):
        state.models[app_label, self.model_name.lower()].fields = [
            (n, self.field if n == self.name else f) for n, f in state.models[app_label, self.model_name.lower()].fields
        ]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.render().get_model(app_label, self.model_name)
        to_model = to_state.render().get_model(app_label, self.model_name)
        schema_editor.alter_field(
            from_model,
            from_model._meta.get_field_by_name(self.name)[0],
            to_model._meta.get_field_by_name(self.name)[0],
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Alter field %s on %s" % (self.name, self.model_name)


class RenameField(Operation):
    """
    Renames a field on the model. Might affect db_column too.
    """

    def __init__(self, model_name, old_name, new_name):
        self.model_name = model_name
        self.old_name = old_name
        self.new_name = new_name

    def state_forwards(self, app_label, state):
        state.models[app_label, self.model_name.lower()].fields = [
            (self.new_name if n == self.old_name else n, f) for n, f in state.models[app_label, self.model_name.lower()].fields
        ]

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.render().get_model(app_label, self.model_name)
        to_model = to_state.render().get_model(app_label, self.model_name)
        schema_editor.alter_field(
            from_model,
            from_model._meta.get_field_by_name(self.old_name)[0],
            to_model._meta.get_field_by_name(self.new_name)[0],
        )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.render().get_model(app_label, self.model_name)
        to_model = to_state.render().get_model(app_label, self.model_name)
        schema_editor.alter_field(
            from_model,
            from_model._meta.get_field_by_name(self.new_name)[0],
            to_model._meta.get_field_by_name(self.old_name)[0],
        )

    def describe(self):
        return "Rename field %s on %s to %s" % (self.old_name, self.model_name, self.new_name)
