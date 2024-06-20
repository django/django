from django.db import models
from django.db.migrations.operations.base import Operation, OperationCategory
from django.db.migrations.state import ModelState
from django.db.migrations.utils import field_references, resolve_relation
from django.db.models.options import normalize_together
from django.utils.functional import cached_property

from .fields import AddField, AlterField, FieldOperation, RemoveField, RenameField


def _check_for_duplicates(arg_name, objs):
    used_vals = set()
    for val in objs:
        if val in used_vals:
            raise ValueError(
                "Found duplicate value %s in CreateModel %s argument." % (val, arg_name)
            )
        used_vals.add(val)


class ModelOperation(Operation):
    def __init__(self, name):
        self.name = name

    @cached_property
    def name_lower(self):
        return self.name.lower()

    def references_model(self, name, app_label):
        return name.lower() == self.name_lower

    def reduce(self, operation, app_label):
        return super().reduce(operation, app_label) or self.can_reduce_through(
            operation, app_label
        )

    def can_reduce_through(self, operation, app_label):
        return not operation.references_model(self.name, app_label)


class CreateModel(ModelOperation):
    """Create a model's table."""

    category = OperationCategory.ADDITION
    serialization_expand_args = ["fields", "options", "managers"]

    def __init__(self, name, fields, options=None, bases=None, managers=None):
        self.fields = fields
        self.options = options or {}
        self.bases = bases or (models.Model,)
        self.managers = managers or []
        super().__init__(name)
        # Sanity-check that there are no duplicated field names, bases, or
        # manager names
        _check_for_duplicates("fields", (name for name, _ in self.fields))
        _check_for_duplicates(
            "bases",
            (
                (
                    base._meta.label_lower
                    if hasattr(base, "_meta")
                    else base.lower() if isinstance(base, str) else base
                )
                for base in self.bases
            ),
        )
        _check_for_duplicates("managers", (name for name, _ in self.managers))

    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "fields": self.fields,
        }
        if self.options:
            kwargs["options"] = self.options
        if self.bases and self.bases != (models.Model,):
            kwargs["bases"] = self.bases
        if self.managers and self.managers != [("objects", models.Manager())]:
            kwargs["managers"] = self.managers
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.add_model(
            ModelState(
                app_label,
                self.name,
                list(self.fields),
                dict(self.options),
                tuple(self.bases),
                list(self.managers),
            )
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    def describe(self):
        return "Create %smodel %s" % (
            "proxy " if self.options.get("proxy", False) else "",
            self.name,
        )

    @property
    def migration_name_fragment(self):
        return self.name_lower

    def references_model(self, name, app_label):
        name_lower = name.lower()
        if name_lower == self.name_lower:
            return True

        # Check we didn't inherit from the model
        reference_model_tuple = (app_label, name_lower)
        for base in self.bases:
            if (
                base is not models.Model
                and isinstance(base, (models.base.ModelBase, str))
                and resolve_relation(base, app_label) == reference_model_tuple
            ):
                return True

        # Check we have no FKs/M2Ms with it
        for _name, field in self.fields:
            if field_references(
                (app_label, self.name_lower), field, reference_model_tuple
            ):
                return True
        return False

    def reduce(self, operation, app_label):
        if (
            isinstance(operation, DeleteModel)
            and self.name_lower == operation.name_lower
            and not self.options.get("proxy", False)
        ):
            return []
        elif (
            isinstance(operation, RenameModel)
            and self.name_lower == operation.old_name_lower
        ):
            return [
                CreateModel(
                    operation.new_name,
                    fields=self.fields,
                    options=self.options,
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterModelOptions)
            and self.name_lower == operation.name_lower
        ):
            options = {**self.options, **operation.options}
            for key in operation.ALTER_OPTION_KEYS:
                if key not in operation.options:
                    options.pop(key, None)
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options=options,
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterModelManagers)
            and self.name_lower == operation.name_lower
        ):
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options=self.options,
                    bases=self.bases,
                    managers=operation.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterTogetherOptionOperation)
            and self.name_lower == operation.name_lower
        ):
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options={
                        **self.options,
                        **{operation.option_name: operation.option_value},
                    },
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterOrderWithRespectTo)
            and self.name_lower == operation.name_lower
        ):
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options={
                        **self.options,
                        "order_with_respect_to": operation.order_with_respect_to,
                    },
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, FieldOperation)
            and self.name_lower == operation.model_name_lower
        ):
            if isinstance(operation, AddField):
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields + [(operation.name, operation.field)],
                        options=self.options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, AlterField):
                return [
                    CreateModel(
                        self.name,
                        fields=[
                            (n, operation.field if n == operation.name else v)
                            for n, v in self.fields
                        ],
                        options=self.options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RemoveField):
                options = self.options.copy()
                for option_name in ("unique_together", "index_together"):
                    option = options.pop(option_name, None)
                    if option:
                        option = set(
                            filter(
                                bool,
                                (
                                    tuple(
                                        f for f in fields if f != operation.name_lower
                                    )
                                    for fields in option
                                ),
                            )
                        )
                        if option:
                            options[option_name] = option
                order_with_respect_to = options.get("order_with_respect_to")
                if order_with_respect_to == operation.name_lower:
                    del options["order_with_respect_to"]
                return [
                    CreateModel(
                        self.name,
                        fields=[
                            (n, v)
                            for n, v in self.fields
                            if n.lower() != operation.name_lower
                        ],
                        options=options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RenameField):
                options = self.options.copy()
                for option_name in ("unique_together", "index_together"):
                    option = options.get(option_name)
                    if option:
                        options[option_name] = {
                            tuple(
                                operation.new_name if f == operation.old_name else f
                                for f in fields
                            )
                            for fields in option
                        }
                order_with_respect_to = options.get("order_with_respect_to")
                if order_with_respect_to == operation.old_name:
                    options["order_with_respect_to"] = operation.new_name
                return [
                    CreateModel(
                        self.name,
                        fields=[
                            (operation.new_name if n == operation.old_name else n, v)
                            for n, v in self.fields
                        ],
                        options=options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
        elif (
            isinstance(operation, IndexOperation)
            and self.name_lower == operation.model_name_lower
        ):
            if isinstance(operation, AddIndex):
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields,
                        options={
                            **self.options,
                            "indexes": [
                                *self.options.get("indexes", []),
                                operation.index,
                            ],
                        },
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RemoveIndex):
                options_indexes = [
                    index
                    for index in self.options.get("indexes", [])
                    if index.name != operation.name
                ]
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields,
                        options={
                            **self.options,
                            "indexes": options_indexes,
                        },
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, AddConstraint):
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields,
                        options={
                            **self.options,
                            "constraints": [
                                *self.options.get("constraints", []),
                                operation.constraint,
                            ],
                        },
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RemoveConstraint):
                options_constraints = [
                    constraint
                    for constraint in self.options.get("constraints", [])
                    if constraint.name != operation.name
                ]
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields,
                        options={
                            **self.options,
                            "constraints": options_constraints,
                        },
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
        return super().reduce(operation, app_label)


class DeleteModel(ModelOperation):
    """Drop a model's table."""

    category = OperationCategory.REMOVAL

    def deconstruct(self):
        kwargs = {
            "name": self.name,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.remove_model(app_label, self.name_lower)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    def references_model(self, name, app_label):
        # The deleted model could be referencing the specified model through
        # related fields.
        return True

    def describe(self):
        return "Delete model %s" % self.name

    @property
    def migration_name_fragment(self):
        return "delete_%s" % self.name_lower


class RenameModel(ModelOperation):
    """Rename a model."""

    category = OperationCategory.ALTERATION

    def __init__(self, old_name, new_name):
        self.old_name = old_name
        self.new_name = new_name
        super().__init__(old_name)

    @cached_property
    def old_name_lower(self):
        return self.old_name.lower()

    @cached_property
    def new_name_lower(self):
        return self.new_name.lower()

    def deconstruct(self):
        kwargs = {
            "old_name": self.old_name,
            "new_name": self.new_name,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.rename_model(app_label, self.old_name, self.new_name)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.new_name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.old_name)
            # Move the main table
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )
            # Alter the fields pointing to us
            for related_object in old_model._meta.related_objects:
                if related_object.related_model == old_model:
                    model = new_model
                    related_key = (app_label, self.new_name_lower)
                else:
                    related_key = (
                        related_object.related_model._meta.app_label,
                        related_object.related_model._meta.model_name,
                    )
                    model = to_state.apps.get_model(*related_key)
                to_field = to_state.apps.get_model(*related_key)._meta.get_field(
                    related_object.field.name
                )
                schema_editor.alter_field(
                    model,
                    related_object.field,
                    to_field,
                )
            # Rename M2M fields whose name is based on this model's name.
            fields = zip(
                old_model._meta.local_many_to_many, new_model._meta.local_many_to_many
            )
            for old_field, new_field in fields:
                # Skip self-referential fields as these are renamed above.
                if (
                    new_field.model == new_field.related_model
                    or not new_field.remote_field.through._meta.auto_created
                ):
                    continue
                # Rename columns and the M2M table.
                schema_editor._alter_many_to_many(
                    new_model,
                    old_field,
                    new_field,
                    strict=False,
                )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

        self.database_forwards(app_label, schema_editor, from_state, to_state)

        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

    def references_model(self, name, app_label):
        return (
            name.lower() == self.old_name_lower or name.lower() == self.new_name_lower
        )

    def describe(self):
        return "Rename model %s to %s" % (self.old_name, self.new_name)

    @property
    def migration_name_fragment(self):
        return "rename_%s_%s" % (self.old_name_lower, self.new_name_lower)

    def reduce(self, operation, app_label):
        if (
            isinstance(operation, RenameModel)
            and self.new_name_lower == operation.old_name_lower
        ):
            return [
                RenameModel(
                    self.old_name,
                    operation.new_name,
                ),
            ]
        # Skip `ModelOperation.reduce` as we want to run `references_model`
        # against self.new_name.
        return super(ModelOperation, self).reduce(
            operation, app_label
        ) or not operation.references_model(self.new_name, app_label)


class ModelOptionOperation(ModelOperation):
    category = OperationCategory.ALTERATION

    def reduce(self, operation, app_label):
        if (
            isinstance(operation, (self.__class__, DeleteModel))
            and self.name_lower == operation.name_lower
        ):
            return [operation]
        return super().reduce(operation, app_label)


class AlterModelTable(ModelOptionOperation):
    """Rename a model's table."""

    def __init__(self, name, table):
        self.table = table
        super().__init__(name)

    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "table": self.table,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.alter_model_options(app_label, self.name_lower, {"db_table": self.table})

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.name)
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )
            # Rename M2M fields whose name is based on this model's db_table
            for old_field, new_field in zip(
                old_model._meta.local_many_to_many, new_model._meta.local_many_to_many
            ):
                if new_field.remote_field.through._meta.auto_created:
                    schema_editor.alter_db_table(
                        new_field.remote_field.through,
                        old_field.remote_field.through._meta.db_table,
                        new_field.remote_field.through._meta.db_table,
                    )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return "Rename table for %s to %s" % (
            self.name,
            self.table if self.table is not None else "(default)",
        )

    @property
    def migration_name_fragment(self):
        return "alter_%s_table" % self.name_lower


class AlterModelTableComment(ModelOptionOperation):
    def __init__(self, name, table_comment):
        self.table_comment = table_comment
        super().__init__(name)

    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "table_comment": self.table_comment,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label, self.name_lower, {"db_table_comment": self.table_comment}
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.name)
            schema_editor.alter_db_table_comment(
                new_model,
                old_model._meta.db_table_comment,
                new_model._meta.db_table_comment,
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def describe(self):
        return f"Alter {self.name} table comment"

    @property
    def migration_name_fragment(self):
        return f"alter_{self.name_lower}_table_comment"


class AlterTogetherOptionOperation(ModelOptionOperation):
    option_name = None

    def __init__(self, name, option_value):
        if option_value:
            option_value = set(normalize_together(option_value))
        setattr(self, self.option_name, option_value)
        super().__init__(name)

    @cached_property
    def option_value(self):
        return getattr(self, self.option_name)

    def deconstruct(self):
        kwargs = {
            "name": self.name,
            self.option_name: self.option_value,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label,
            self.name_lower,
            {self.option_name: self.option_value},
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.name)
            alter_together = getattr(schema_editor, "alter_%s" % self.option_name)
            alter_together(
                new_model,
                getattr(old_model._meta, self.option_name, set()),
                getattr(new_model._meta, self.option_name, set()),
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    def references_field(self, model_name, name, app_label):
        return self.references_model(model_name, app_label) and (
            not self.option_value
            or any((name in fields) for fields in self.option_value)
        )

    def describe(self):
        return "Alter %s for %s (%s constraint(s))" % (
            self.option_name,
            self.name,
            len(self.option_value or ""),
        )

    @property
    def migration_name_fragment(self):
        return "alter_%s_%s" % (self.name_lower, self.option_name)

    def can_reduce_through(self, operation, app_label):
        return super().can_reduce_through(operation, app_label) or (
            isinstance(operation, AlterTogetherOptionOperation)
            and type(operation) is not type(self)
        )


class AlterUniqueTogether(AlterTogetherOptionOperation):
    """
    Change the value of unique_together to the target one.
    Input value of unique_together must be a set of tuples.
    """

    option_name = "unique_together"

    def __init__(self, name, unique_together):
        super().__init__(name, unique_together)


class AlterIndexTogether(AlterTogetherOptionOperation):
    """
    Change the value of index_together to the target one.
    Input value of index_together must be a set of tuples.
    """

    option_name = "index_together"

    def __init__(self, name, index_together):
        super().__init__(name, index_together)


class AlterOrderWithRespectTo(ModelOptionOperation):
    """Represent a change with the order_with_respect_to option."""

    option_name = "order_with_respect_to"

    def __init__(self, name, order_with_respect_to):
        self.order_with_respect_to = order_with_respect_to
        super().__init__(name)

    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "order_with_respect_to": self.order_with_respect_to,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label,
            self.name_lower,
            {self.option_name: self.order_with_respect_to},
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(app_label, self.name)
            # Remove a field if we need to
            if (
                from_model._meta.order_with_respect_to
                and not to_model._meta.order_with_respect_to
            ):
                schema_editor.remove_field(
                    from_model, from_model._meta.get_field("_order")
                )
            # Add a field if we need to (altering the column is untouched as
            # it's likely a rename)
            elif (
                to_model._meta.order_with_respect_to
                and not from_model._meta.order_with_respect_to
            ):
                field = to_model._meta.get_field("_order")
                if not field.has_default():
                    field.default = 0
                schema_editor.add_field(
                    from_model,
                    field,
                )

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.database_forwards(app_label, schema_editor, from_state, to_state)

    def references_field(self, model_name, name, app_label):
        return self.references_model(model_name, app_label) and (
            self.order_with_respect_to is None or name == self.order_with_respect_to
        )

    def describe(self):
        return "Set order_with_respect_to on %s to %s" % (
            self.name,
            self.order_with_respect_to,
        )

    @property
    def migration_name_fragment(self):
        return "alter_%s_order_with_respect_to" % self.name_lower


class AlterModelOptions(ModelOptionOperation):
    """
    Set new model options that don't directly affect the database schema
    (like verbose_name, permissions, ordering). Python code in migrations
    may still need them.
    """

    # Model options we want to compare and preserve in an AlterModelOptions op
    ALTER_OPTION_KEYS = [
        "base_manager_name",
        "default_manager_name",
        "default_related_name",
        "get_latest_by",
        "managed",
        "ordering",
        "permissions",
        "default_permissions",
        "select_on_save",
        "verbose_name",
        "verbose_name_plural",
    ]

    def __init__(self, name, options):
        self.options = options
        super().__init__(name)

    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "options": self.options,
        }
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label,
            self.name_lower,
            self.options,
            self.ALTER_OPTION_KEYS,
        )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def describe(self):
        return "Change Meta options on %s" % self.name

    @property
    def migration_name_fragment(self):
        return "alter_%s_options" % self.name_lower


class AlterModelManagers(ModelOptionOperation):
    """Alter the model's managers."""

    serialization_expand_args = ["managers"]

    def __init__(self, name, managers):
        self.managers = managers
        super().__init__(name)

    def deconstruct(self):
        return (self.__class__.__qualname__, [self.name, self.managers], {})

    def state_forwards(self, app_label, state):
        state.alter_model_managers(app_label, self.name_lower, self.managers)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    def describe(self):
        return "Change managers on %s" % self.name

    @property
    def migration_name_fragment(self):
        return "alter_%s_managers" % self.name_lower


class IndexOperation(Operation):
    option_name = "indexes"

    @cached_property
    def model_name_lower(self):
        return self.model_name.lower()


class AddIndex(IndexOperation):
    """Add an index on a model."""

    category = OperationCategory.ADDITION

    def __init__(self, model_name, index):
        self.model_name = model_name
        if not index.name:
            raise ValueError(
                "Indexes passed to AddIndex operations require a name "
                "argument. %r doesn't have one." % index
            )
        self.index = index

    def state_forwards(self, app_label, state):
        state.add_index(app_label, self.model_name_lower, self.index)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.add_index(model, self.index)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.remove_index(model, self.index)

    def deconstruct(self):
        kwargs = {
            "model_name": self.model_name,
            "index": self.index,
        }
        return (
            self.__class__.__qualname__,
            [],
            kwargs,
        )

    def describe(self):
        if self.index.expressions:
            return "Create index %s on %s on model %s" % (
                self.index.name,
                ", ".join([str(expression) for expression in self.index.expressions]),
                self.model_name,
            )
        return "Create index %s on field(s) %s of model %s" % (
            self.index.name,
            ", ".join(self.index.fields),
            self.model_name,
        )

    @property
    def migration_name_fragment(self):
        return "%s_%s" % (self.model_name_lower, self.index.name.lower())

    def reduce(self, operation, app_label):
        if isinstance(operation, RemoveIndex) and self.index.name == operation.name:
            return []
        if isinstance(operation, RenameIndex) and self.index.name == operation.old_name:
            self.index.name = operation.new_name
            return [AddIndex(model_name=self.model_name, index=self.index)]
        return super().reduce(operation, app_label)


class RemoveIndex(IndexOperation):
    """Remove an index from a model."""

    category = OperationCategory.REMOVAL

    def __init__(self, model_name, name):
        self.model_name = model_name
        self.name = name

    def state_forwards(self, app_label, state):
        state.remove_index(app_label, self.model_name_lower, self.name)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            from_model_state = from_state.models[app_label, self.model_name_lower]
            index = from_model_state.get_index_by_name(self.name)
            schema_editor.remove_index(model, index)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            to_model_state = to_state.models[app_label, self.model_name_lower]
            index = to_model_state.get_index_by_name(self.name)
            schema_editor.add_index(model, index)

    def deconstruct(self):
        kwargs = {
            "model_name": self.model_name,
            "name": self.name,
        }
        return (
            self.__class__.__qualname__,
            [],
            kwargs,
        )

    def describe(self):
        return "Remove index %s from %s" % (self.name, self.model_name)

    @property
    def migration_name_fragment(self):
        return "remove_%s_%s" % (self.model_name_lower, self.name.lower())


class RenameIndex(IndexOperation):
    """Rename an index."""

    category = OperationCategory.ALTERATION

    def __init__(self, model_name, new_name, old_name=None, old_fields=None):
        if not old_name and not old_fields:
            raise ValueError(
                "RenameIndex requires one of old_name and old_fields arguments to be "
                "set."
            )
        if old_name and old_fields:
            raise ValueError(
                "RenameIndex.old_name and old_fields are mutually exclusive."
            )
        self.model_name = model_name
        self.new_name = new_name
        self.old_name = old_name
        self.old_fields = old_fields

    @cached_property
    def old_name_lower(self):
        return self.old_name.lower()

    @cached_property
    def new_name_lower(self):
        return self.new_name.lower()

    def deconstruct(self):
        kwargs = {
            "model_name": self.model_name,
            "new_name": self.new_name,
        }
        if self.old_name:
            kwargs["old_name"] = self.old_name
        if self.old_fields:
            kwargs["old_fields"] = self.old_fields
        return (self.__class__.__qualname__, [], kwargs)

    def state_forwards(self, app_label, state):
        if self.old_fields:
            state.add_index(
                app_label,
                self.model_name_lower,
                models.Index(fields=self.old_fields, name=self.new_name),
            )
            state.remove_model_options(
                app_label,
                self.model_name_lower,
                AlterIndexTogether.option_name,
                self.old_fields,
            )
        else:
            state.rename_index(
                app_label, self.model_name_lower, self.old_name, self.new_name
            )

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, model):
            return

        if self.old_fields:
            from_model = from_state.apps.get_model(app_label, self.model_name)
            columns = [
                from_model._meta.get_field(field).column for field in self.old_fields
            ]
            matching_index_name = schema_editor._constraint_names(
                from_model,
                column_names=columns,
                index=True,
                unique=False,
            )
            if len(matching_index_name) != 1:
                raise ValueError(
                    "Found wrong number (%s) of indexes for %s(%s)."
                    % (
                        len(matching_index_name),
                        from_model._meta.db_table,
                        ", ".join(columns),
                    )
                )
            old_index = models.Index(
                fields=self.old_fields,
                name=matching_index_name[0],
            )
        else:
            from_model_state = from_state.models[app_label, self.model_name_lower]
            old_index = from_model_state.get_index_by_name(self.old_name)
        # Don't alter when the index name is not changed.
        if old_index.name == self.new_name:
            return

        to_model_state = to_state.models[app_label, self.model_name_lower]
        new_index = to_model_state.get_index_by_name(self.new_name)
        schema_editor.rename_index(model, old_index, new_index)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if self.old_fields:
            # Backward operation with unnamed index is a no-op.
            return

        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

        self.database_forwards(app_label, schema_editor, from_state, to_state)

        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

    def describe(self):
        if self.old_name:
            return (
                f"Rename index {self.old_name} on {self.model_name} to {self.new_name}"
            )
        return (
            f"Rename unnamed index for {self.old_fields} on {self.model_name} to "
            f"{self.new_name}"
        )

    @property
    def migration_name_fragment(self):
        if self.old_name:
            return "rename_%s_%s" % (self.old_name_lower, self.new_name_lower)
        return "rename_%s_%s_%s" % (
            self.model_name_lower,
            "_".join(self.old_fields),
            self.new_name_lower,
        )

    def reduce(self, operation, app_label):
        if (
            isinstance(operation, RenameIndex)
            and self.model_name_lower == operation.model_name_lower
            and operation.old_name
            and self.new_name_lower == operation.old_name_lower
        ):
            return [
                RenameIndex(
                    self.model_name,
                    new_name=operation.new_name,
                    old_name=self.old_name,
                    old_fields=self.old_fields,
                )
            ]
        return super().reduce(operation, app_label)


class AddConstraint(IndexOperation):
    category = OperationCategory.ADDITION
    option_name = "constraints"

    def __init__(self, model_name, constraint):
        self.model_name = model_name
        self.constraint = constraint

    def state_forwards(self, app_label, state):
        state.add_constraint(app_label, self.model_name_lower, self.constraint)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.add_constraint(model, self.constraint)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.remove_constraint(model, self.constraint)

    def deconstruct(self):
        return (
            self.__class__.__name__,
            [],
            {
                "model_name": self.model_name,
                "constraint": self.constraint,
            },
        )

    def describe(self):
        return "Create constraint %s on model %s" % (
            self.constraint.name,
            self.model_name,
        )

    @property
    def migration_name_fragment(self):
        return "%s_%s" % (self.model_name_lower, self.constraint.name.lower())

    def reduce(self, operation, app_label):
        if (
            isinstance(operation, RemoveConstraint)
            and self.model_name_lower == operation.model_name_lower
            and self.constraint.name == operation.name
        ):
            return []
        return super().reduce(operation, app_label)


class RemoveConstraint(IndexOperation):
    category = OperationCategory.REMOVAL
    option_name = "constraints"

    def __init__(self, model_name, name):
        self.model_name = model_name
        self.name = name

    def state_forwards(self, app_label, state):
        state.remove_constraint(app_label, self.model_name_lower, self.name)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            from_model_state = from_state.models[app_label, self.model_name_lower]
            constraint = from_model_state.get_constraint_by_name(self.name)
            schema_editor.remove_constraint(model, constraint)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            to_model_state = to_state.models[app_label, self.model_name_lower]
            constraint = to_model_state.get_constraint_by_name(self.name)
            schema_editor.add_constraint(model, constraint)

    def deconstruct(self):
        return (
            self.__class__.__name__,
            [],
            {
                "model_name": self.model_name,
                "name": self.name,
            },
        )

    def describe(self):
        return "Remove constraint %s from model %s" % (self.name, self.model_name)

    @property
    def migration_name_fragment(self):
        return "remove_%s_%s" % (self.model_name_lower, self.name.lower())
