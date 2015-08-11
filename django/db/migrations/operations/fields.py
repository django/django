from __future__ import unicode_literals

from django.db.models.fields import NOT_PROVIDED
from django.utils import six
from django.utils.functional import cached_property

from .base import Operation


class AddField(Operation):
    """
    Adds a field to a model.
    """

    def __init__(self, model_name, name, field, preserve_default=True):
        self.model_name = model_name
        self.name = name
        self.field = field
        self.preserve_default = preserve_default

    @cached_property
    def name_lower(self):
        return self.name.lower()

    @cached_property
    def model_name_lower(self):
        return self.model_name.lower()

    def deconstruct(self):
        kwargs = {
            'model_name': self.model_name,
            'name': self.name,
            'field': self.field,
        }
        if self.preserve_default is not True:
            kwargs['preserve_default'] = self.preserve_default
        return (
            self.__class__.__name__,
            [],
            kwargs
        )

    def state_forwards(self, app_label, state):
        # If preserve default is off, don't use the default for future state
        if not self.preserve_default:
            field = self.field.clone()
            field.default = NOT_PROVIDED
        else:
            field = self.field
        state.models[app_label, self.model_name_lower].fields.append((self.name, field))
        state.reload_model(app_label, self.model_name_lower)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(app_label, self.model_name)
            field = to_model._meta.get_field(self.name)
            if not self.preserve_default:
                field.default = self.field.default
            schema_editor.add_field(
                from_model,
                field,
            )
            if not self.preserve_default:
                field.default = NOT_PROVIDED

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, from_model):
            schema_editor.remove_field(from_model, from_model._meta.get_field(self.name))

    def describe(self):
        return "Add field %s to %s" % (self.name, self.model_name)

    def references_model(self, name, app_label=None):
        return name.lower() == self.model_name_lower

    def references_field(self, model_name, name, app_label=None):
        return self.references_model(model_name) and name.lower() == self.name_lower


class RemoveField(Operation):
    """
    Removes a field from a model.
    """

    def __init__(self, model_name, name):
        self.model_name = model_name
        self.name = name

    @cached_property
    def name_lower(self):
        return self.name.lower()

    @cached_property
    def model_name_lower(self):
        return self.model_name.lower()

    def deconstruct(self):
        kwargs = {
            'model_name': self.model_name,
            'name': self.name,
        }
        return (
            self.__class__.__name__,
            [],
            kwargs
        )

    def state_forwards(self, app_label, state):
        new_fields = []
        for name, instance in state.models[app_label, self.model_name_lower].fields:
            if name != self.name:
                new_fields.append((name, instance))
        state.models[app_label, self.model_name_lower].fields = new_fields
        state.reload_model(app_label, self.model_name_lower)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        from_model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, from_model):
            schema_editor.remove_field(from_model, from_model._meta.get_field(self.name))

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.add_field(from_model, to_model._meta.get_field(self.name))

    def describe(self):
        return "Remove field %s from %s" % (self.name, self.model_name)

    def references_model(self, name, app_label=None):
        return name.lower() == self.model_name_lower

    def references_field(self, model_name, name, app_label=None):
        return self.references_model(model_name) and name.lower() == self.name_lower


class AlterField(Operation):
    """
    Alters a field's database column (e.g. null, max_length) to the provided new field
    """

    def __init__(self, model_name, name, field, preserve_default=True):
        self.model_name = model_name
        self.name = name
        self.field = field
        self.preserve_default = preserve_default

    @cached_property
    def name_lower(self):
        return self.name.lower()

    @cached_property
    def model_name_lower(self):
        return self.model_name.lower()

    def deconstruct(self):
        kwargs = {
            'model_name': self.model_name,
            'name': self.name,
            'field': self.field,
        }
        if self.preserve_default is not True:
            kwargs['preserve_default'] = self.preserve_default
        return (
            self.__class__.__name__,
            [],
            kwargs
        )

    def state_forwards(self, app_label, state):
        if not self.preserve_default:
            field = self.field.clone()
            field.default = NOT_PROVIDED
        else:
            field = self.field
        state.models[app_label, self.model_name_lower].fields = [
            (n, field if n == self.name else f)
            for n, f in
            state.models[app_label, self.model_name_lower].fields
        ]
        state.reload_model(app_label, self.model_name_lower)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(app_label, self.model_name)
            from_field = from_model._meta.get_field(self.name)
            to_field = to_model._meta.get_field(self.name)
            # If the field is a relatedfield with an unresolved rel.to, just
            # set it equal to the other field side. Bandaid fix for AlterField
            # migrations that are part of a RenameModel change.
            if from_field.remote_field and from_field.remote_field.model:
                if isinstance(from_field.remote_field.model, six.string_types):
                    from_field.remote_field.model = to_field.remote_field.model
                elif to_field.remote_field and isinstance(to_field.remote_field.model, six.string_types):
                    to_field.remote_field.model = from_field.remote_field.model
            if not self.preserve_default:
                to_field.default = self.field.default
            schema_editor.alter_field(from_model, from_field, to_field)
            if not self.preserve_default:
                to_field.default = NOT_PROVIDED

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Alter field %s on %s" % (self.name, self.model_name)

    def references_model(self, name, app_label=None):
        return name.lower() == self.model_name_lower

    def references_field(self, model_name, name, app_label=None):
        return self.references_model(model_name) and name.lower() == self.name_lower


class RenameField(Operation):
    """
    Renames a field on the model. Might affect db_column too.
    """

    def __init__(self, model_name, old_name, new_name):
        self.model_name = model_name
        self.old_name = old_name
        self.new_name = new_name

    @cached_property
    def old_name_lower(self):
        return self.old_name.lower()

    @cached_property
    def new_name_lower(self):
        return self.new_name.lower()

    @cached_property
    def model_name_lower(self):
        return self.model_name.lower()

    def deconstruct(self):
        kwargs = {
            'model_name': self.model_name,
            'old_name': self.old_name,
            'new_name': self.new_name,
        }
        return (
            self.__class__.__name__,
            [],
            kwargs
        )

    def state_forwards(self, app_label, state):
        # Rename the field
        state.models[app_label, self.model_name_lower].fields = [
            (self.new_name if n == self.old_name else n, f)
            for n, f in state.models[app_label, self.model_name_lower].fields
        ]
        # Fix index/unique_together to refer to the new field
        options = state.models[app_label, self.model_name_lower].options
        for option in ('index_together', 'unique_together'):
            if option in options:
                options[option] = [
                    [self.new_name if n == self.old_name else n for n in together]
                    for together in options[option]
                ]
        state.reload_model(app_label, self.model_name_lower)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.alter_field(
                from_model,
                from_model._meta.get_field(self.old_name),
                to_model._meta.get_field(self.new_name),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(app_label, self.model_name)
            schema_editor.alter_field(
                from_model,
                from_model._meta.get_field(self.new_name),
                to_model._meta.get_field(self.old_name),
            )

    def describe(self):
        return "Rename field %s on %s to %s" % (self.old_name, self.model_name, self.new_name)

    def references_model(self, name, app_label=None):
        return name.lower() == self.model_name_lower

    def references_field(self, model_name, name, app_label=None):
        return self.references_model(model_name) and (
            name.lower() == self.old_name_lower or
            name.lower() == self.new_name_lower
        )
