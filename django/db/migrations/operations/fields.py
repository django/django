from .base import Operation


class AddField(Operation):
    """
    Adds a field to a model.
    """

    def __init__(self, model_name, name, instance):
        self.model_name = model_name
        self.name = name
        self.instance = instance

    def state_forwards(self, app_label, state):
        state.models[app_label, self.model_name.lower()].fields.append((self.name, self.instance))

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = to_state.render()
        model = app_cache.get_model(app_label, self.model_name)
        schema_editor.add_field(model, model._meta.get_field_by_name(self.name)[0])

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = from_state.render()
        model = app_cache.get_model(app_label, self.model_name)
        schema_editor.remove_field(model, model._meta.get_field_by_name(self.name)[0])


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
        app_cache = from_state.render()
        model = app_cache.get_model(app_label, self.model_name)
        schema_editor.remove_field(model, model._meta.get_field_by_name(self.name)[0])

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        app_cache = to_state.render()
        model = app_cache.get_model(app_label, self.model_name)
        schema_editor.add_field(model, model._meta.get_field_by_name(self.name)[0])
