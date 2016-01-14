from __future__ import unicode_literals

from django.db.migrations import (
    AddField, AlterField, AlterIndexTogether, AlterModelTable,
    AlterOrderWithRespectTo, AlterUniqueTogether, CreateModel, DeleteModel,
    RemoveField, RenameField, RenameModel,
)
from django.utils import six


class MigrationOptimizer(object):
    """
    Powers the optimization process, where you provide a list of Operations
    and you are returned a list of equal or shorter length - operations
    are merged into one if possible.

    For example, a CreateModel and an AddField can be optimized into a
    new CreateModel, and CreateModel and DeleteModel can be optimized into
    nothing.
    """

    def __init__(self):
        self.model_level_operations = (
            CreateModel,
            AlterModelTable,
            AlterUniqueTogether,
            AlterIndexTogether,
            AlterOrderWithRespectTo,
        )
        self.field_level_operations = (
            AddField,
            AlterField,
        )
        self.reduce_methods = {
            # (model operation, model operation)
            (CreateModel, DeleteModel): self.reduce_create_model_delete_model,
            (CreateModel, RenameModel): self.reduce_create_model_rename_model,
            (RenameModel, RenameModel): self.reduce_rename_model_rename_model,

            (AlterIndexTogether, AlterIndexTogether): self.reduce_alter_model_alter_model,
            (AlterModelTable, AlterModelTable): self.reduce_alter_model_alter_model,
            (AlterOrderWithRespectTo, AlterOrderWithRespectTo): self.reduce_alter_model_alter_model,
            (AlterUniqueTogether, AlterUniqueTogether): self.reduce_alter_model_alter_model,

            (AlterIndexTogether, DeleteModel): self.reduce_alter_model_delete_model,
            (AlterModelTable, DeleteModel): self.reduce_alter_model_delete_model,
            (AlterOrderWithRespectTo, DeleteModel): self.reduce_alter_model_delete_model,
            (AlterUniqueTogether, DeleteModel): self.reduce_alter_model_delete_model,

            # (model operation, field operation)
            (CreateModel, AddField): self.reduce_create_model_add_field,
            (CreateModel, AlterField): self.reduce_create_model_alter_field,
            (CreateModel, RemoveField): self.reduce_create_model_remove_field,
            (CreateModel, RenameField): self.reduce_create_model_rename_field,

            (AlterIndexTogether, AddField): self.reduce_alter_model_addalterremove_field,
            (AlterIndexTogether, AlterField): self.reduce_alter_model_addalterremove_field,
            (AlterIndexTogether, RemoveField): self.reduce_alter_model_addalterremove_field,
            (AlterOrderWithRespectTo, AddField): self.reduce_alter_model_addalterremove_field,
            (AlterOrderWithRespectTo, AlterField): self.reduce_alter_model_addalterremove_field,
            (AlterOrderWithRespectTo, RemoveField): self.reduce_alter_model_addalterremove_field,
            (AlterUniqueTogether, AddField): self.reduce_alter_model_addalterremove_field,
            (AlterUniqueTogether, AlterField): self.reduce_alter_model_addalterremove_field,
            (AlterUniqueTogether, RemoveField): self.reduce_alter_model_addalterremove_field,

            (AlterIndexTogether, RenameField): self.reduce_alter_model_rename_field,
            (AlterOrderWithRespectTo, RenameField): self.reduce_alter_model_rename_field,
            (AlterUniqueTogether, RenameField): self.reduce_alter_model_rename_field,

            # (field operation, field operation)
            (AddField, AlterField): self.reduce_add_field_alter_field,
            (AddField, RemoveField): self.reduce_add_field_remove_field,
            (AddField, RenameField): self.reduce_add_field_rename_field,
            (AlterField, RemoveField): self.reduce_alter_field_remove_field,
            (AlterField, RenameField): self.reduce_alter_field_rename_field,
            (RenameField, RenameField): self.reduce_rename_field_rename_field,
        }

    def optimize(self, operations, app_label=None):
        """
        Main optimization entry point. Pass in a list of Operation instances,
        get out a new list of Operation instances.

        Unfortunately, due to the scope of the optimization (two combinable
        operations might be separated by several hundred others), this can't be
        done as a peephole optimization with checks/output implemented on
        the Operations themselves; instead, the optimizer looks at each
        individual operation and scans forwards in the list to see if there
        are any matches, stopping at boundaries - operations which can't
        be optimized over (RunSQL, operations on the same field/model, etc.)

        The inner loop is run until the starting list is the same as the result
        list, and then the result is returned. This means that operation
        optimization must be stable and always return an equal or shorter list.

        The app_label argument is optional, but if you pass it you'll get more
        efficient optimization.
        """
        # Internal tracking variable for test assertions about # of loops
        self._iterations = 0
        while True:
            result = self.optimize_inner(operations, app_label)
            self._iterations += 1
            if result == operations:
                return result
            operations = result

    def optimize_inner(self, operations, app_label=None):
        """
        Inner optimization loop.
        """
        new_operations = []
        for i, operation in enumerate(operations):
            # Compare it to each operation after it
            for j, other in enumerate(operations[i + 1:]):
                result = self.reduce(operation, other, operations[i + 1:i + j + 1])
                if result is not None:
                    # Optimize! Add result, then remaining others, then return
                    new_operations.extend(result)
                    new_operations.extend(operations[i + 1:i + 1 + j])
                    new_operations.extend(operations[i + j + 2:])
                    return new_operations
                if not self.can_optimize_through(operation, other, app_label):
                    new_operations.append(operation)
                    break
            else:
                new_operations.append(operation)
        return new_operations

    # REDUCTION

    def reduce(self, operation, other, in_between=None):
        """
        Either returns a list of zero, one or two operations,
        or None, meaning this pair cannot be optimized.
        """
        method = self.reduce_methods.get((type(operation), type(other)))
        if method:
            return method(operation, other, in_between or [])
        return None

    def model_to_key(self, model):
        """
        Takes either a model class or a "appname.ModelName" string
        and returns (appname, modelname)
        """
        if isinstance(model, six.string_types):
            return model.split(".", 1)
        else:
            return (
                model._meta.app_label,
                model._meta.object_name,
            )

    # REDUCE METHODS: (MODEL OPERATION, MODEL OPERATION)

    def reduce_create_model_delete_model(self, operation, other, in_between):
        """
        Folds a CreateModel and a DeleteModel into nothing.
        """
        if (operation.name_lower == other.name_lower and
                not operation.options.get("proxy", False)):
            return []

    def reduce_create_model_rename_model(self, operation, other, in_between):
        """
        Folds a model rename into its create
        """
        if operation.name_lower == other.old_name_lower:
            return [
                CreateModel(
                    other.new_name,
                    fields=operation.fields,
                    options=operation.options,
                    bases=operation.bases,
                    managers=operation.managers,
                )
            ]

    def reduce_rename_model_rename_model(self, operation, other, in_between):
        """
        Folds a model rename into another one
        """
        if operation.new_name_lower == other.old_name_lower:
            return [
                RenameModel(
                    operation.old_name,
                    other.new_name,
                )
            ]

    def reduce_alter_model_alter_model(self, operation, other, in_between):
        """
        Folds two AlterModelTable, AlterFooTogether, or AlterOrderWithRespectTo
        operations into the latter.
        """
        if operation.name_lower == other.name_lower:
            return [other]

    def reduce_alter_model_delete_model(self, operation, other, in_between):
        """
        Folds an AlterModelSomething and a DeleteModel into just delete.
        """
        if operation.name_lower == other.name_lower:
            return [other]

    # REDUCE METHODS: (MODEL OPERATION, FIELD OPERATION)

    def reduce_create_model_add_field(self, operation, other, in_between):
        if operation.name_lower == other.model_name_lower:
            # Don't allow optimizations of FKs through models they reference
            if hasattr(other.field, "remote_field") and other.field.remote_field:
                for between in in_between:
                    # Check that it doesn't point to the model
                    app_label, object_name = self.model_to_key(other.field.remote_field.model)
                    if between.references_model(object_name, app_label):
                        return None
                    # Check that it's not through the model
                    if getattr(other.field.remote_field, "through", None):
                        app_label, object_name = self.model_to_key(other.field.remote_field.through)
                        if between.references_model(object_name, app_label):
                            return None
            # OK, that's fine
            return [
                CreateModel(
                    operation.name,
                    fields=operation.fields + [(other.name, other.field)],
                    options=operation.options,
                    bases=operation.bases,
                    managers=operation.managers,
                )
            ]

    def reduce_create_model_alter_field(self, operation, other, in_between):
        if operation.name_lower == other.model_name_lower:
            return [
                CreateModel(
                    operation.name,
                    fields=[
                        (n, other.field if n == other.name else v)
                        for n, v in operation.fields
                    ],
                    options=operation.options,
                    bases=operation.bases,
                    managers=operation.managers,
                )
            ]

    def reduce_create_model_remove_field(self, operation, other, in_between):
        if operation.name_lower == other.model_name_lower:
            return [
                CreateModel(
                    operation.name,
                    fields=[
                        (n, v)
                        for n, v in operation.fields
                        if n.lower() != other.name_lower
                    ],
                    options=operation.options,
                    bases=operation.bases,
                    managers=operation.managers,
                )
            ]

    def reduce_create_model_rename_field(self, operation, other, in_between):
        if operation.name_lower == other.model_name_lower:
            return [
                CreateModel(
                    operation.name,
                    fields=[
                        (other.new_name if n == other.old_name else n, v)
                        for n, v in operation.fields
                    ],
                    options=operation.options,
                    bases=operation.bases,
                    managers=operation.managers,
                )
            ]

    def reduce_alter_model_addalterremove_field(self, operation, other, in_between):
        if (operation.name_lower == other.model_name_lower and
                not operation.references_field(other.model_name, other.name)):
            return [other, operation]

    def reduce_alter_model_rename_field(self, operation, other, in_between):
        if (operation.name_lower == other.model_name_lower and
                not operation.references_field(other.model_name, other.old_name)):
            return [other, operation]

    # REDUCE METHODS: (FIELD OPERATION, FIELD OPERATION)

    def reduce_add_field_alter_field(self, operation, other, in_between):
        if (operation.model_name_lower == other.model_name_lower and
                operation.name_lower == other.name_lower):
            return [
                AddField(
                    model_name=operation.model_name,
                    name=operation.name,
                    field=other.field,
                )
            ]

    def reduce_add_field_remove_field(self, operation, other, in_between):
        if (operation.model_name_lower == other.model_name_lower and
                operation.name_lower == other.name_lower):
            return []

    def reduce_add_field_rename_field(self, operation, other, in_between):
        if (operation.model_name_lower == other.model_name_lower and
                operation.name_lower == other.old_name_lower):
            return [
                AddField(
                    model_name=operation.model_name,
                    name=other.new_name,
                    field=operation.field,
                )
            ]

    def reduce_alter_field_remove_field(self, operation, other, in_between):
        if (operation.model_name_lower == other.model_name_lower and
                operation.name_lower == other.name_lower):
            return [other]

    def reduce_alter_field_rename_field(self, operation, other, in_between):
        if (operation.model_name_lower == other.model_name_lower and
                operation.name_lower == other.old_name_lower):
            return [
                other,
                AlterField(
                    model_name=operation.model_name,
                    name=other.new_name,
                    field=operation.field,
                ),
            ]

    def reduce_rename_field_rename_field(self, operation, other, in_between):
        if (operation.model_name_lower == other.model_name_lower and
                operation.new_name_lower == other.old_name_lower):
            return [
                RenameField(
                    operation.model_name,
                    operation.old_name,
                    other.new_name,
                ),
            ]

    # THROUGH CHECKS

    def can_optimize_through(self, operation, other, app_label=None):
        """
        Returns True if it's possible to optimize 'operation' with something
        the other side of 'other'. This is possible if, for example, they
        affect different models.
        """
        # If it's a model level operation, let it through if there's
        # nothing that looks like a reference to us in 'other'.
        if isinstance(operation, self.model_level_operations):
            if not other.references_model(operation.name, app_label):
                return True
        # If it's field level, only let it through things that don't reference
        # the field (which includes not referencing the model)
        if isinstance(operation, self.field_level_operations):
            if not other.references_field(operation.model_name, operation.name, app_label):
                return True
        return False
