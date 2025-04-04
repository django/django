import functools
import re
from collections import defaultdict, namedtuple
from enum import Enum
from graphlib import TopologicalSorter
from itertools import chain

from django.conf import settings
from django.db import models
from django.db.migrations import operations
from django.db.migrations.migration import Migration
from django.db.migrations.operations.models import AlterModelOptions
from django.db.migrations.optimizer import MigrationOptimizer
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.utils import (
    COMPILED_REGEX_TYPE,
    RegexObject,
    resolve_relation,
)
from django.utils.functional import cached_property


class OperationDependency(
    namedtuple("OperationDependency", "app_label model_name field_name type")
):
    class Type(Enum):
        CREATE = 0
        REMOVE = 1
        ALTER = 2
        REMOVE_ORDER_WRT = 3
        ALTER_FOO_TOGETHER = 4

    @cached_property
    def model_name_lower(self):
        return self.model_name.lower()

    @cached_property
    def field_name_lower(self):
        return self.field_name.lower()


class MigrationAutodetector:
    """
    Take a pair of ProjectStates and compare them to see what the first would
    need doing to make it match the second (the second usually being the
    project's current state).

    Note that this naturally operates on entire projects at a time,
    as it's likely that changes interact (for example, you can't
    add a ForeignKey without having a migration to add the table it
    depends on first). A user interface may offer single-app usage
    if it wishes, with the caveat that it may not always be possible.
    """

    def __init__(self, from_state, to_state, questioner=None):
        self.from_state = from_state
        self.to_state = to_state
        self.questioner = questioner or MigrationQuestioner()
        self.existing_apps = {app for app, model in from_state.models}

    def changes(self, graph, trim_to_apps=None, convert_apps=None, migration_name=None):
        """
        Main entry point to produce a list of applicable changes.
        Take a graph to base names on and an optional set of apps
        to try and restrict to (restriction is not guaranteed)
        """
        changes = self._detect_changes(convert_apps, graph)
        changes = self.arrange_for_graph(changes, graph, migration_name)
        if trim_to_apps:
            changes = self._trim_to_apps(changes, trim_to_apps)
        return changes

    def deep_deconstruct(self, obj):
        """
        Recursive deconstruction for a field and its arguments.
        Used for full comparison for rename/alter; sometimes a single-level
        deconstruction will not compare correctly.
        """
        if isinstance(obj, list):
            return [self.deep_deconstruct(value) for value in obj]
        elif isinstance(obj, tuple):
            return tuple(self.deep_deconstruct(value) for value in obj)
        elif isinstance(obj, dict):
            return {key: self.deep_deconstruct(value) for key, value in obj.items()}
        elif isinstance(obj, functools.partial):
            return (
                obj.func,
                self.deep_deconstruct(obj.args),
                self.deep_deconstruct(obj.keywords),
            )
        elif isinstance(obj, COMPILED_REGEX_TYPE):
            return RegexObject(obj)
        elif isinstance(obj, type):
            # If this is a type that implements 'deconstruct' as an instance method,
            # avoid treating this as being deconstructible itself - see #22951
            return obj
        elif hasattr(obj, "deconstruct"):
            deconstructed = obj.deconstruct()
            if isinstance(obj, models.Field):
                # we have a field which also returns a name
                deconstructed = deconstructed[1:]
            path, args, kwargs = deconstructed
            return (
                path,
                [self.deep_deconstruct(value) for value in args],
                {key: self.deep_deconstruct(value) for key, value in kwargs.items()},
            )
        else:
            return obj

    def only_relation_agnostic_fields(self, fields):
        """
        Return a definition of the fields that ignores field names and
        what related fields actually relate to. Used for detecting renames (as
        the related fields change during renames).
        """
        fields_def = []
        for name, field in sorted(fields.items()):
            deconstruction = self.deep_deconstruct(field)
            if field.remote_field and field.remote_field.model:
                deconstruction[2].pop("to", None)
            fields_def.append(deconstruction)
        return fields_def

    def _detect_changes(self, convert_apps=None, graph=None):
        """
        Return a dict of migration plans which will achieve the
        change from from_state to to_state. The dict has app labels
        as keys and a list of migrations as values.

        The resulting migrations aren't specially named, but the names
        do matter for dependencies inside the set.

        convert_apps is the list of apps to convert to use migrations
        (i.e. to make initial migrations for, in the usual case)

        graph is an optional argument that, if provided, can help improve
        dependency generation and avoid potential circular dependencies.
        """
        # The first phase is generating all the operations for each app
        # and gathering them into a big per-app list.
        # Then go through that list, order it, and split into migrations to
        # resolve dependencies caused by M2Ms and FKs.
        self.generated_operations = {}
        self.altered_indexes = {}
        self.altered_constraints = {}
        self.renamed_fields = {}

        # Prepare some old/new state and model lists, separating
        # proxy models and ignoring unmigrated apps.
        self.old_model_keys = set()
        self.old_proxy_keys = set()
        self.old_unmanaged_keys = set()
        self.new_model_keys = set()
        self.new_proxy_keys = set()
        self.new_unmanaged_keys = set()
        for (app_label, model_name), model_state in self.from_state.models.items():
            if not model_state.options.get("managed", True):
                self.old_unmanaged_keys.add((app_label, model_name))
            elif app_label not in self.from_state.real_apps:
                if model_state.options.get("proxy"):
                    self.old_proxy_keys.add((app_label, model_name))
                else:
                    self.old_model_keys.add((app_label, model_name))

        for (app_label, model_name), model_state in self.to_state.models.items():
            if not model_state.options.get("managed", True):
                self.new_unmanaged_keys.add((app_label, model_name))
            elif app_label not in self.from_state.real_apps or (
                convert_apps and app_label in convert_apps
            ):
                if model_state.options.get("proxy"):
                    self.new_proxy_keys.add((app_label, model_name))
                else:
                    self.new_model_keys.add((app_label, model_name))

        self.from_state.resolve_fields_and_relations()
        self.to_state.resolve_fields_and_relations()

        # Renames have to come first
        self.generate_renamed_models()

        # Prepare lists of fields and generate through model map
        self._prepare_field_lists()
        self._generate_through_model_map()

        # Generate non-rename model operations
        self.generate_deleted_models()
        self.generate_created_models()
        self.generate_deleted_proxies()
        self.generate_created_proxies()
        self.generate_altered_options()
        self.generate_altered_managers()
        self.generate_altered_db_table_comment()

        # Create the renamed fields and store them in self.renamed_fields.
        # They are used by create_altered_indexes(), generate_altered_fields(),
        # generate_removed_altered_index/unique_together(), and
        # generate_altered_index/unique_together().
        self.create_renamed_fields()
        # Create the altered indexes and store them in self.altered_indexes.
        # This avoids the same computation in generate_removed_indexes()
        # and generate_added_indexes().
        self.create_altered_indexes()
        self.create_altered_constraints()
        # Generate index removal operations before field is removed
        self.generate_removed_constraints()
        self.generate_removed_indexes()
        # Generate field renaming operations.
        self.generate_renamed_fields()
        self.generate_renamed_indexes()
        # Generate removal of foo together.
        self.generate_removed_altered_unique_together()
        # Generate field operations.
        self.generate_removed_fields()
        self.generate_added_fields()
        self.generate_altered_fields()
        self.generate_altered_order_with_respect_to()
        self.generate_altered_unique_together()
        self.generate_added_indexes()
        self.generate_added_constraints()
        self.generate_altered_constraints()
        self.generate_altered_db_table()

        self._sort_migrations()
        self._build_migration_list(graph)
        self._optimize_migrations()

        return self.migrations

    def _prepare_field_lists(self):
        """
        Prepare field lists and a list of the fields that used through models
        in the old state so dependencies can be made from the through model
        deletion to the field that uses it.
        """
        self.kept_model_keys = self.old_model_keys & self.new_model_keys
        self.kept_proxy_keys = self.old_proxy_keys & self.new_proxy_keys
        self.kept_unmanaged_keys = self.old_unmanaged_keys & self.new_unmanaged_keys
        self.through_users = {}
        self.old_field_keys = {
            (app_label, model_name, field_name)
            for app_label, model_name in self.kept_model_keys
            for field_name in self.from_state.models[
                app_label, self.renamed_models.get((app_label, model_name), model_name)
            ].fields
        }
        self.new_field_keys = {
            (app_label, model_name, field_name)
            for app_label, model_name in self.kept_model_keys
            for field_name in self.to_state.models[app_label, model_name].fields
        }

    def _generate_through_model_map(self):
        """Through model map generation."""
        for app_label, model_name in sorted(self.old_model_keys):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            for field_name, field in old_model_state.fields.items():
                if hasattr(field, "remote_field") and getattr(
                    field.remote_field, "through", None
                ):
                    through_key = resolve_relation(
                        field.remote_field.through, app_label, model_name
                    )
                    self.through_users[through_key] = (
                        app_label,
                        old_model_name,
                        field_name,
                    )

    @staticmethod
    def _resolve_dependency(dependency):
        """
        Return the resolved dependency and a boolean denoting whether or not
        it was swappable.
        """
        if dependency.app_label != "__setting__":
            return dependency, False
        resolved_app_label, resolved_object_name = getattr(
            settings, dependency.model_name
        ).split(".")
        return (
            OperationDependency(
                resolved_app_label,
                resolved_object_name.lower(),
                dependency.field_name,
                dependency.type,
            ),
            True,
        )

    def _build_migration_list(self, graph=None):
        """
        Chop the lists of operations up into migrations with dependencies on
        each other. Do this by going through an app's list of operations until
        one is found that has an outgoing dependency that isn't in another
        app's migration yet (hasn't been chopped off its list). Then chop off
        the operations before it into a migration and move onto the next app.
        If the loops completes without doing anything, there's a circular
        dependency (which _should_ be impossible as the operations are
        all split at this point so they can't depend and be depended on).
        """
        self.migrations = {}
        num_ops = sum(len(x) for x in self.generated_operations.values())
        chop_mode = False
        while num_ops:
            # On every iteration, we step through all the apps and see if there
            # is a completed set of operations.
            # If we find that a subset of the operations are complete we can
            # try to chop it off from the rest and continue, but we only
            # do this if we've already been through the list once before
            # without any chopping and nothing has changed.
            for app_label in sorted(self.generated_operations):
                chopped = []
                dependencies = set()
                for operation in list(self.generated_operations[app_label]):
                    deps_satisfied = True
                    operation_dependencies = set()
                    for dep in operation._auto_deps:
                        # Temporarily resolve the swappable dependency to
                        # prevent circular references. While keeping the
                        # dependency checks on the resolved model, add the
                        # swappable dependencies.
                        original_dep = dep
                        dep, is_swappable_dep = self._resolve_dependency(dep)
                        if dep.app_label != app_label:
                            # External app dependency. See if it's not yet
                            # satisfied.
                            for other_operation in self.generated_operations.get(
                                dep.app_label, []
                            ):
                                if self.check_dependency(other_operation, dep):
                                    deps_satisfied = False
                                    break
                            if not deps_satisfied:
                                break
                            else:
                                if is_swappable_dep:
                                    operation_dependencies.add(
                                        (
                                            original_dep.app_label,
                                            original_dep.model_name,
                                        )
                                    )
                                elif dep.app_label in self.migrations:
                                    operation_dependencies.add(
                                        (
                                            dep.app_label,
                                            self.migrations[dep.app_label][-1].name,
                                        )
                                    )
                                else:
                                    # If we can't find the other app, we add a
                                    # first/last dependency, but only if we've
                                    # already been through once and checked
                                    # everything.
                                    if chop_mode:
                                        # If the app already exists, we add a
                                        # dependency on the last migration, as
                                        # we don't know which migration
                                        # contains the target field. If it's
                                        # not yet migrated or has no
                                        # migrations, we use __first__.
                                        if graph and graph.leaf_nodes(dep.app_label):
                                            operation_dependencies.add(
                                                graph.leaf_nodes(dep.app_label)[0]
                                            )
                                        else:
                                            operation_dependencies.add(
                                                (dep.app_label, "__first__")
                                            )
                                    else:
                                        deps_satisfied = False
                    if deps_satisfied:
                        chopped.append(operation)
                        dependencies.update(operation_dependencies)
                        del self.generated_operations[app_label][0]
                    else:
                        break
                # Make a migration! Well, only if there's stuff to put in it
                if dependencies or chopped:
                    if not self.generated_operations[app_label] or chop_mode:
                        subclass = type(
                            "Migration",
                            (Migration,),
                            {"operations": [], "dependencies": []},
                        )
                        instance = subclass(
                            "auto_%i" % (len(self.migrations.get(app_label, [])) + 1),
                            app_label,
                        )
                        instance.dependencies = list(dependencies)
                        instance.operations = chopped
                        instance.initial = app_label not in self.existing_apps
                        self.migrations.setdefault(app_label, []).append(instance)
                        chop_mode = False
                    else:
                        self.generated_operations[app_label] = (
                            chopped + self.generated_operations[app_label]
                        )
            new_num_ops = sum(len(x) for x in self.generated_operations.values())
            if new_num_ops == num_ops:
                if not chop_mode:
                    chop_mode = True
                else:
                    raise ValueError(
                        "Cannot resolve operation dependencies: %r"
                        % self.generated_operations
                    )
            num_ops = new_num_ops

    def _sort_migrations(self):
        """
        Reorder to make things possible. Reordering may be needed so FKs work
        nicely inside the same app.
        """
        for app_label, ops in sorted(self.generated_operations.items()):
            ts = TopologicalSorter()
            for op in ops:
                ts.add(op)
                for dep in op._auto_deps:
                    # Resolve intra-app dependencies to handle circular
                    # references involving a swappable model.
                    dep = self._resolve_dependency(dep)[0]
                    if dep.app_label != app_label:
                        continue
                    ts.add(op, *(x for x in ops if self.check_dependency(x, dep)))
            self.generated_operations[app_label] = list(ts.static_order())

    def _optimize_migrations(self):
        # Add in internal dependencies among the migrations
        for app_label, migrations in self.migrations.items():
            for m1, m2 in zip(migrations, migrations[1:]):
                m2.dependencies.append((app_label, m1.name))

        # De-dupe dependencies
        for migrations in self.migrations.values():
            for migration in migrations:
                migration.dependencies = list(set(migration.dependencies))

        # Optimize migrations
        for app_label, migrations in self.migrations.items():
            for migration in migrations:
                migration.operations = MigrationOptimizer().optimize(
                    migration.operations, app_label
                )

    def check_dependency(self, operation, dependency):
        """
        Return True if the given operation depends on the given dependency,
        False otherwise.
        """
        # Created model
        if (
            dependency.field_name is None
            and dependency.type == OperationDependency.Type.CREATE
        ):
            return (
                isinstance(operation, operations.CreateModel)
                and operation.name_lower == dependency.model_name_lower
            )
        # Created field
        elif (
            dependency.field_name is not None
            and dependency.type == OperationDependency.Type.CREATE
        ):
            return (
                isinstance(operation, operations.CreateModel)
                and operation.name_lower == dependency.model_name_lower
                and any(dependency.field_name == x for x, y in operation.fields)
            ) or (
                isinstance(operation, operations.AddField)
                and operation.model_name_lower == dependency.model_name_lower
                and operation.name_lower == dependency.field_name_lower
            )
        # Removed field
        elif (
            dependency.field_name is not None
            and dependency.type == OperationDependency.Type.REMOVE
        ):
            return (
                isinstance(operation, operations.RemoveField)
                and operation.model_name_lower == dependency.model_name_lower
                and operation.name_lower == dependency.field_name_lower
            )
        # Removed model
        elif (
            dependency.field_name is None
            and dependency.type == OperationDependency.Type.REMOVE
        ):
            return (
                isinstance(operation, operations.DeleteModel)
                and operation.name_lower == dependency.model_name_lower
            )
        # Field being altered
        elif (
            dependency.field_name is not None
            and dependency.type == OperationDependency.Type.ALTER
        ):
            return (
                isinstance(operation, operations.AlterField)
                and operation.model_name_lower == dependency.model_name_lower
                and operation.name_lower == dependency.field_name_lower
            )
        # order_with_respect_to being unset for a field
        elif (
            dependency.field_name is not None
            and dependency.type == OperationDependency.Type.REMOVE_ORDER_WRT
        ):
            return (
                isinstance(operation, operations.AlterOrderWithRespectTo)
                and operation.name_lower == dependency.model_name_lower
                and (operation.order_with_respect_to or "").lower()
                != dependency.field_name_lower
            )
        # Field is removed and part of an index/unique_together
        elif (
            dependency.field_name is not None
            and dependency.type == OperationDependency.Type.ALTER_FOO_TOGETHER
        ):
            return (
                isinstance(
                    operation,
                    (operations.AlterUniqueTogether, operations.AlterIndexTogether),
                )
                and operation.name_lower == dependency.model_name_lower
            )
        # Unknown dependency. Raise an error.
        else:
            raise ValueError("Can't handle dependency %r" % (dependency,))

    def add_operation(self, app_label, operation, dependencies=None, beginning=False):
        # Dependencies are
        # (app_label, model_name, field_name, create/delete as True/False)
        operation._auto_deps = dependencies or []
        if beginning:
            self.generated_operations.setdefault(app_label, []).insert(0, operation)
        else:
            self.generated_operations.setdefault(app_label, []).append(operation)

    def swappable_first_key(self, item):
        """
        Place potential swappable models first in lists of created models (only
        real way to solve #22783).
        """
        try:
            model_state = self.to_state.models[item]
            base_names = {
                base if isinstance(base, str) else base.__name__
                for base in model_state.bases
            }
            string_version = "%s.%s" % (item[0], item[1])
            if (
                model_state.options.get("swappable")
                or "AbstractUser" in base_names
                or "AbstractBaseUser" in base_names
                or settings.AUTH_USER_MODEL.lower() == string_version.lower()
            ):
                return ("___" + item[0], "___" + item[1])
        except LookupError:
            pass
        return item

    def generate_renamed_models(self):
        """
        Find any renamed models, generate the operations for them, and remove
        the old entry from the model lists. Must be run before other
        model-level generation.
        """
        self.renamed_models = {}
        self.renamed_models_rel = {}
        added_models = self.new_model_keys - self.old_model_keys
        for app_label, model_name in sorted(added_models):
            model_state = self.to_state.models[app_label, model_name]
            model_fields_def = self.only_relation_agnostic_fields(model_state.fields)

            removed_models = self.old_model_keys - self.new_model_keys
            for rem_app_label, rem_model_name in removed_models:
                if rem_app_label == app_label:
                    rem_model_state = self.from_state.models[
                        rem_app_label, rem_model_name
                    ]
                    rem_model_fields_def = self.only_relation_agnostic_fields(
                        rem_model_state.fields
                    )
                    if model_fields_def == rem_model_fields_def:
                        if self.questioner.ask_rename_model(
                            rem_model_state, model_state
                        ):
                            dependencies = []
                            fields = list(model_state.fields.values()) + [
                                field.remote_field
                                for relations in self.to_state.relations[
                                    app_label, model_name
                                ].values()
                                for field in relations.values()
                            ]
                            for field in fields:
                                if field.is_relation:
                                    dependencies.extend(
                                        self._get_dependencies_for_foreign_key(
                                            app_label,
                                            model_name,
                                            field,
                                            self.to_state,
                                        )
                                    )
                            self.add_operation(
                                app_label,
                                operations.RenameModel(
                                    old_name=rem_model_state.name,
                                    new_name=model_state.name,
                                ),
                                dependencies=dependencies,
                            )
                            self.renamed_models[app_label, model_name] = rem_model_name
                            renamed_models_rel_key = "%s.%s" % (
                                rem_model_state.app_label,
                                rem_model_state.name_lower,
                            )
                            self.renamed_models_rel[renamed_models_rel_key] = (
                                "%s.%s"
                                % (
                                    model_state.app_label,
                                    model_state.name_lower,
                                )
                            )
                            self.old_model_keys.remove((rem_app_label, rem_model_name))
                            self.old_model_keys.add((app_label, model_name))
                            break

    def generate_created_models(self):
        """
        Find all new models (both managed and unmanaged) and make create
        operations for them as well as separate operations to create any
        foreign key or M2M relationships (these are optimized later, if
        possible).

        Defer any model options that refer to collections of fields that might
        be deferred (e.g. unique_together).
        """
        old_keys = self.old_model_keys | self.old_unmanaged_keys
        added_models = self.new_model_keys - old_keys
        added_unmanaged_models = self.new_unmanaged_keys - old_keys
        all_added_models = chain(
            sorted(added_models, key=self.swappable_first_key, reverse=True),
            sorted(added_unmanaged_models, key=self.swappable_first_key, reverse=True),
        )
        for app_label, model_name in all_added_models:
            model_state = self.to_state.models[app_label, model_name]
            # Gather related fields
            related_fields = {}
            primary_key_rel = None
            for field_name, field in model_state.fields.items():
                if field.remote_field:
                    if field.remote_field.model:
                        if field.primary_key:
                            primary_key_rel = field.remote_field.model
                        elif not field.remote_field.parent_link:
                            related_fields[field_name] = field
                    if getattr(field.remote_field, "through", None):
                        related_fields[field_name] = field

            # Are there indexes/unique_together to defer?
            indexes = model_state.options.pop("indexes")
            constraints = model_state.options.pop("constraints")
            unique_together = model_state.options.pop("unique_together", None)
            order_with_respect_to = model_state.options.pop(
                "order_with_respect_to", None
            )
            # Depend on the deletion of any possible proxy version of us
            dependencies = [
                OperationDependency(
                    app_label, model_name, None, OperationDependency.Type.REMOVE
                ),
            ]
            # Depend on all bases
            for base in model_state.bases:
                if isinstance(base, str) and "." in base:
                    base_app_label, base_name = base.split(".", 1)
                    dependencies.append(
                        OperationDependency(
                            base_app_label,
                            base_name,
                            None,
                            OperationDependency.Type.CREATE,
                        )
                    )
                    # Depend on the removal of base fields if the new model has
                    # a field with the same name.
                    old_base_model_state = self.from_state.models.get(
                        (base_app_label, base_name)
                    )
                    new_base_model_state = self.to_state.models.get(
                        (base_app_label, base_name)
                    )
                    if old_base_model_state and new_base_model_state:
                        removed_base_fields = (
                            set(old_base_model_state.fields)
                            .difference(
                                new_base_model_state.fields,
                            )
                            .intersection(model_state.fields)
                        )
                        for removed_base_field in removed_base_fields:
                            dependencies.append(
                                OperationDependency(
                                    base_app_label,
                                    base_name,
                                    removed_base_field,
                                    OperationDependency.Type.REMOVE,
                                )
                            )
            # Depend on the other end of the primary key if it's a relation
            if primary_key_rel:
                dependencies.append(
                    OperationDependency(
                        *resolve_relation(primary_key_rel, app_label, model_name),
                        None,
                        OperationDependency.Type.CREATE,
                    ),
                )
            # Generate creation operation
            self.add_operation(
                app_label,
                operations.CreateModel(
                    name=model_state.name,
                    fields=[
                        d
                        for d in model_state.fields.items()
                        if d[0] not in related_fields
                    ],
                    options=model_state.options,
                    bases=model_state.bases,
                    managers=model_state.managers,
                ),
                dependencies=dependencies,
                beginning=True,
            )

            # Don't add operations which modify the database for unmanaged models
            if not model_state.options.get("managed", True):
                continue

            # Generate operations for each related field
            for name, field in sorted(related_fields.items()):
                dependencies = self._get_dependencies_for_foreign_key(
                    app_label,
                    model_name,
                    field,
                    self.to_state,
                )
                # Depend on our own model being created
                dependencies.append(
                    OperationDependency(
                        app_label, model_name, None, OperationDependency.Type.CREATE
                    )
                )
                # Make operation
                self.add_operation(
                    app_label,
                    operations.AddField(
                        model_name=model_name,
                        name=name,
                        field=field,
                    ),
                    dependencies=list(set(dependencies)),
                )
            # Generate other opns
            if order_with_respect_to:
                self.add_operation(
                    app_label,
                    operations.AlterOrderWithRespectTo(
                        name=model_name,
                        order_with_respect_to=order_with_respect_to,
                    ),
                    dependencies=[
                        OperationDependency(
                            app_label,
                            model_name,
                            order_with_respect_to,
                            OperationDependency.Type.CREATE,
                        ),
                        OperationDependency(
                            app_label, model_name, None, OperationDependency.Type.CREATE
                        ),
                    ],
                )
            related_dependencies = [
                OperationDependency(
                    app_label, model_name, name, OperationDependency.Type.CREATE
                )
                for name in sorted(related_fields)
            ]
            related_dependencies.append(
                OperationDependency(
                    app_label, model_name, None, OperationDependency.Type.CREATE
                )
            )
            for index in indexes:
                self.add_operation(
                    app_label,
                    operations.AddIndex(
                        model_name=model_name,
                        index=index,
                    ),
                    dependencies=related_dependencies,
                )
            for constraint in constraints:
                self.add_operation(
                    app_label,
                    operations.AddConstraint(
                        model_name=model_name,
                        constraint=constraint,
                    ),
                    dependencies=related_dependencies,
                )
            if unique_together:
                self.add_operation(
                    app_label,
                    operations.AlterUniqueTogether(
                        name=model_name,
                        unique_together=unique_together,
                    ),
                    dependencies=related_dependencies,
                )
            # Fix relationships if the model changed from a proxy model to a
            # concrete model.
            relations = self.to_state.relations
            if (app_label, model_name) in self.old_proxy_keys:
                for related_model_key, related_fields in relations[
                    app_label, model_name
                ].items():
                    related_model_state = self.to_state.models[related_model_key]
                    for related_field_name, related_field in related_fields.items():
                        self.add_operation(
                            related_model_state.app_label,
                            operations.AlterField(
                                model_name=related_model_state.name,
                                name=related_field_name,
                                field=related_field,
                            ),
                            dependencies=[
                                OperationDependency(
                                    app_label,
                                    model_name,
                                    None,
                                    OperationDependency.Type.CREATE,
                                )
                            ],
                        )

    def generate_created_proxies(self):
        """
        Make CreateModel statements for proxy models. Use the same statements
        as that way there's less code duplication, but for proxy models it's
        safe to skip all the pointless field stuff and chuck out an operation.
        """
        added = self.new_proxy_keys - self.old_proxy_keys
        for app_label, model_name in sorted(added):
            model_state = self.to_state.models[app_label, model_name]
            assert model_state.options.get("proxy")
            # Depend on the deletion of any possible non-proxy version of us
            dependencies = [
                OperationDependency(
                    app_label, model_name, None, OperationDependency.Type.REMOVE
                ),
            ]
            # Depend on all bases
            for base in model_state.bases:
                if isinstance(base, str) and "." in base:
                    base_app_label, base_name = base.split(".", 1)
                    dependencies.append(
                        OperationDependency(
                            base_app_label,
                            base_name,
                            None,
                            OperationDependency.Type.CREATE,
                        )
                    )
            # Generate creation operation
            self.add_operation(
                app_label,
                operations.CreateModel(
                    name=model_state.name,
                    fields=[],
                    options=model_state.options,
                    bases=model_state.bases,
                    managers=model_state.managers,
                ),
                # Depend on the deletion of any possible non-proxy version of us
                dependencies=dependencies,
            )

    def generate_deleted_models(self):
        """
        Find all deleted models (managed and unmanaged) and make delete
        operations for them as well as separate operations to delete any
        foreign key or M2M relationships (these are optimized later, if
        possible).

        Also bring forward removal of any model options that refer to
        collections of fields - the inverse of generate_created_models().
        """
        new_keys = self.new_model_keys | self.new_unmanaged_keys
        deleted_models = self.old_model_keys - new_keys
        deleted_unmanaged_models = self.old_unmanaged_keys - new_keys
        all_deleted_models = chain(
            sorted(deleted_models), sorted(deleted_unmanaged_models)
        )
        for app_label, model_name in all_deleted_models:
            model_state = self.from_state.models[app_label, model_name]
            # Gather related fields
            related_fields = {}
            for field_name, field in model_state.fields.items():
                if field.remote_field:
                    if field.remote_field.model:
                        related_fields[field_name] = field
                    if getattr(field.remote_field, "through", None):
                        related_fields[field_name] = field
            # Generate option removal first
            unique_together = model_state.options.pop("unique_together", None)
            if unique_together:
                self.add_operation(
                    app_label,
                    operations.AlterUniqueTogether(
                        name=model_name,
                        unique_together=None,
                    ),
                )
            # Then remove each related field
            for name in sorted(related_fields):
                self.add_operation(
                    app_label,
                    operations.RemoveField(
                        model_name=model_name,
                        name=name,
                    ),
                )
            # Finally, remove the model.
            # This depends on both the removal/alteration of all incoming fields
            # and the removal of all its own related fields, and if it's
            # a through model the field that references it.
            dependencies = []
            relations = self.from_state.relations
            for (
                related_object_app_label,
                object_name,
            ), relation_related_fields in relations[app_label, model_name].items():
                for field_name, field in relation_related_fields.items():
                    dependencies.append(
                        OperationDependency(
                            related_object_app_label,
                            object_name,
                            field_name,
                            OperationDependency.Type.REMOVE,
                        ),
                    )
                    if not field.many_to_many:
                        dependencies.append(
                            OperationDependency(
                                related_object_app_label,
                                object_name,
                                field_name,
                                OperationDependency.Type.ALTER,
                            ),
                        )

            for name in sorted(related_fields):
                dependencies.append(
                    OperationDependency(
                        app_label, model_name, name, OperationDependency.Type.REMOVE
                    )
                )
            # We're referenced in another field's through=
            through_user = self.through_users.get((app_label, model_state.name_lower))
            if through_user:
                dependencies.append(
                    OperationDependency(*through_user, OperationDependency.Type.REMOVE),
                )
            # Finally, make the operation, deduping any dependencies
            self.add_operation(
                app_label,
                operations.DeleteModel(
                    name=model_state.name,
                ),
                dependencies=list(set(dependencies)),
            )

    def generate_deleted_proxies(self):
        """Make DeleteModel options for proxy models."""
        deleted = self.old_proxy_keys - self.new_proxy_keys
        for app_label, model_name in sorted(deleted):
            model_state = self.from_state.models[app_label, model_name]
            assert model_state.options.get("proxy")
            self.add_operation(
                app_label,
                operations.DeleteModel(
                    name=model_state.name,
                ),
            )

    def create_renamed_fields(self):
        """Work out renamed fields."""
        self.renamed_operations = []
        old_field_keys = self.old_field_keys.copy()
        for app_label, model_name, field_name in sorted(
            self.new_field_keys - old_field_keys
        ):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            field = new_model_state.get_field(field_name)
            # Scan to see if this is actually a rename!
            field_dec = self.deep_deconstruct(field)
            for rem_app_label, rem_model_name, rem_field_name in sorted(
                old_field_keys - self.new_field_keys
            ):
                if rem_app_label == app_label and rem_model_name == model_name:
                    old_field = old_model_state.get_field(rem_field_name)
                    old_field_dec = self.deep_deconstruct(old_field)
                    if (
                        field.remote_field
                        and field.remote_field.model
                        and "to" in old_field_dec[2]
                    ):
                        old_rel_to = old_field_dec[2]["to"]
                        if old_rel_to in self.renamed_models_rel:
                            old_field_dec[2]["to"] = self.renamed_models_rel[old_rel_to]
                    old_field.set_attributes_from_name(rem_field_name)
                    old_db_column = old_field.get_attname_column()[1]
                    if old_field_dec == field_dec or (
                        # Was the field renamed and db_column equal to the
                        # old field's column added?
                        old_field_dec[0:2] == field_dec[0:2]
                        and dict(old_field_dec[2], db_column=old_db_column)
                        == field_dec[2]
                    ):
                        if self.questioner.ask_rename(
                            model_name, rem_field_name, field_name, field
                        ):
                            self.renamed_operations.append(
                                (
                                    rem_app_label,
                                    rem_model_name,
                                    old_field.db_column,
                                    rem_field_name,
                                    app_label,
                                    model_name,
                                    field,
                                    field_name,
                                )
                            )
                            old_field_keys.remove(
                                (rem_app_label, rem_model_name, rem_field_name)
                            )
                            old_field_keys.add((app_label, model_name, field_name))
                            self.renamed_fields[app_label, model_name, field_name] = (
                                rem_field_name
                            )
                            break

    def generate_renamed_fields(self):
        """Generate RenameField operations."""
        for (
            rem_app_label,
            rem_model_name,
            rem_db_column,
            rem_field_name,
            app_label,
            model_name,
            field,
            field_name,
        ) in self.renamed_operations:
            # A db_column mismatch requires a prior noop AlterField for the
            # subsequent RenameField to be a noop on attempts at preserving the
            # old name.
            if rem_db_column != field.db_column:
                altered_field = field.clone()
                altered_field.name = rem_field_name
                self.add_operation(
                    app_label,
                    operations.AlterField(
                        model_name=model_name,
                        name=rem_field_name,
                        field=altered_field,
                    ),
                )
            self.add_operation(
                app_label,
                operations.RenameField(
                    model_name=model_name,
                    old_name=rem_field_name,
                    new_name=field_name,
                ),
            )
            self.old_field_keys.remove((rem_app_label, rem_model_name, rem_field_name))
            self.old_field_keys.add((app_label, model_name, field_name))

    def generate_added_fields(self):
        """Make AddField operations."""
        for app_label, model_name, field_name in sorted(
            self.new_field_keys - self.old_field_keys
        ):
            self._generate_added_field(app_label, model_name, field_name)

    def _generate_added_field(self, app_label, model_name, field_name):
        field = self.to_state.models[app_label, model_name].get_field(field_name)
        # Adding a field always depends at least on its removal.
        dependencies = [
            OperationDependency(
                app_label, model_name, field_name, OperationDependency.Type.REMOVE
            )
        ]
        # Fields that are foreignkeys/m2ms depend on stuff.
        if field.remote_field and field.remote_field.model:
            dependencies.extend(
                self._get_dependencies_for_foreign_key(
                    app_label,
                    model_name,
                    field,
                    self.to_state,
                )
            )
        if field.generated:
            dependencies.extend(self._get_dependencies_for_generated_field(field))
        # You can't just add NOT NULL fields with no default or fields
        # which don't allow empty strings as default.
        time_fields = (models.DateField, models.DateTimeField, models.TimeField)
        preserve_default = (
            field.null
            or field.has_default()
            or field.db_default is not models.NOT_PROVIDED
            or field.many_to_many
            or (field.blank and field.empty_strings_allowed)
            or (isinstance(field, time_fields) and field.auto_now)
        )
        if not preserve_default:
            field = field.clone()
            if isinstance(field, time_fields) and field.auto_now_add:
                field.default = self.questioner.ask_auto_now_add_addition(
                    field_name, model_name
                )
            else:
                field.default = self.questioner.ask_not_null_addition(
                    field_name, model_name
                )
        if (
            field.unique
            and field.default is not models.NOT_PROVIDED
            and callable(field.default)
        ):
            self.questioner.ask_unique_callable_default_addition(field_name, model_name)
        self.add_operation(
            app_label,
            operations.AddField(
                model_name=model_name,
                name=field_name,
                field=field,
                preserve_default=preserve_default,
            ),
            dependencies=dependencies,
        )

    def generate_removed_fields(self):
        """Make RemoveField operations."""
        for app_label, model_name, field_name in sorted(
            self.old_field_keys - self.new_field_keys
        ):
            self._generate_removed_field(app_label, model_name, field_name)

    def _generate_removed_field(self, app_label, model_name, field_name):
        self.add_operation(
            app_label,
            operations.RemoveField(
                model_name=model_name,
                name=field_name,
            ),
            # We might need to depend on the removal of an
            # order_with_respect_to or index/unique_together operation;
            # this is safely ignored if there isn't one
            dependencies=[
                OperationDependency(
                    app_label,
                    model_name,
                    field_name,
                    OperationDependency.Type.REMOVE_ORDER_WRT,
                ),
                OperationDependency(
                    app_label,
                    model_name,
                    field_name,
                    OperationDependency.Type.ALTER_FOO_TOGETHER,
                ),
            ],
        )

    def generate_altered_fields(self):
        """
        Make AlterField operations, or possibly RemovedField/AddField if alter
        isn't possible.
        """
        for app_label, model_name, field_name in sorted(
            self.old_field_keys & self.new_field_keys
        ):
            # Did the field change?
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_field_name = self.renamed_fields.get(
                (app_label, model_name, field_name), field_name
            )
            old_field = self.from_state.models[app_label, old_model_name].get_field(
                old_field_name
            )
            new_field = self.to_state.models[app_label, model_name].get_field(
                field_name
            )
            dependencies = []
            # Implement any model renames on relations; these are handled by RenameModel
            # so we need to exclude them from the comparison
            if hasattr(new_field, "remote_field") and getattr(
                new_field.remote_field, "model", None
            ):
                rename_key = resolve_relation(
                    new_field.remote_field.model, app_label, model_name
                )
                if rename_key in self.renamed_models:
                    new_field.remote_field.model = old_field.remote_field.model
                # Handle ForeignKey which can only have a single to_field.
                remote_field_name = getattr(new_field.remote_field, "field_name", None)
                if remote_field_name:
                    to_field_rename_key = rename_key + (remote_field_name,)
                    if to_field_rename_key in self.renamed_fields:
                        # Repoint both model and field name because to_field
                        # inclusion in ForeignKey.deconstruct() is based on
                        # both.
                        new_field.remote_field.model = old_field.remote_field.model
                        new_field.remote_field.field_name = (
                            old_field.remote_field.field_name
                        )
                # Handle ForeignObjects which can have multiple from_fields/to_fields.
                from_fields = getattr(new_field, "from_fields", None)
                if from_fields:
                    from_rename_key = (app_label, model_name)
                    new_field.from_fields = tuple(
                        [
                            self.renamed_fields.get(
                                from_rename_key + (from_field,), from_field
                            )
                            for from_field in from_fields
                        ]
                    )
                    new_field.to_fields = tuple(
                        [
                            self.renamed_fields.get(rename_key + (to_field,), to_field)
                            for to_field in new_field.to_fields
                        ]
                    )
                    if old_from_fields := getattr(old_field, "from_fields", None):
                        old_field.from_fields = tuple(old_from_fields)
                        old_field.to_fields = tuple(old_field.to_fields)
                dependencies.extend(
                    self._get_dependencies_for_foreign_key(
                        app_label,
                        model_name,
                        new_field,
                        self.to_state,
                    )
                )
            if hasattr(new_field, "remote_field") and getattr(
                new_field.remote_field, "through", None
            ):
                rename_key = resolve_relation(
                    new_field.remote_field.through, app_label, model_name
                )
                if rename_key in self.renamed_models:
                    new_field.remote_field.through = old_field.remote_field.through
            old_field_dec = self.deep_deconstruct(old_field)
            new_field_dec = self.deep_deconstruct(new_field)
            # If the field was confirmed to be renamed it means that only
            # db_column was allowed to change which generate_renamed_fields()
            # already accounts for by adding an AlterField operation.
            if old_field_dec != new_field_dec and old_field_name == field_name:
                both_m2m = old_field.many_to_many and new_field.many_to_many
                neither_m2m = not old_field.many_to_many and not new_field.many_to_many
                if both_m2m or neither_m2m:
                    # Either both fields are m2m or neither is
                    preserve_default = True
                    if (
                        old_field.null
                        and not new_field.null
                        and not new_field.has_default()
                        and new_field.db_default is models.NOT_PROVIDED
                        and not new_field.many_to_many
                    ):
                        field = new_field.clone()
                        new_default = self.questioner.ask_not_null_alteration(
                            field_name, model_name
                        )
                        if new_default is not models.NOT_PROVIDED:
                            field.default = new_default
                            preserve_default = False
                    else:
                        field = new_field
                    self.add_operation(
                        app_label,
                        operations.AlterField(
                            model_name=model_name,
                            name=field_name,
                            field=field,
                            preserve_default=preserve_default,
                        ),
                        dependencies=dependencies,
                    )
                else:
                    # We cannot alter between m2m and concrete fields
                    self._generate_removed_field(app_label, model_name, field_name)
                    self._generate_added_field(app_label, model_name, field_name)

    def create_altered_indexes(self):
        option_name = operations.AddIndex.option_name
        self.renamed_index_together_values = defaultdict(list)

        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]

            old_indexes = old_model_state.options[option_name]
            new_indexes = new_model_state.options[option_name]
            added_indexes = [idx for idx in new_indexes if idx not in old_indexes]
            removed_indexes = [idx for idx in old_indexes if idx not in new_indexes]
            renamed_indexes = []
            # Find renamed indexes.
            remove_from_added = []
            remove_from_removed = []
            for new_index in added_indexes:
                new_index_dec = new_index.deconstruct()
                new_index_name = new_index_dec[2].pop("name")
                for old_index in removed_indexes:
                    old_index_dec = old_index.deconstruct()
                    old_index_name = old_index_dec[2].pop("name")
                    # Indexes are the same except for the names.
                    if (
                        new_index_dec == old_index_dec
                        and new_index_name != old_index_name
                    ):
                        renamed_indexes.append((old_index_name, new_index_name, None))
                        remove_from_added.append(new_index)
                        remove_from_removed.append(old_index)
            # Find index_together changed to indexes.
            for (
                old_value,
                new_value,
                index_together_app_label,
                index_together_model_name,
                dependencies,
            ) in self._get_altered_foo_together_operations(
                operations.AlterIndexTogether.option_name
            ):
                if (
                    app_label != index_together_app_label
                    or model_name != index_together_model_name
                ):
                    continue
                removed_values = old_value.difference(new_value)
                for removed_index_together in removed_values:
                    renamed_index_together_indexes = []
                    for new_index in added_indexes:
                        _, args, kwargs = new_index.deconstruct()
                        # Ensure only 'fields' are defined in the Index.
                        if (
                            not args
                            and new_index.fields == list(removed_index_together)
                            and set(kwargs) == {"name", "fields"}
                        ):
                            renamed_index_together_indexes.append(new_index)

                    if len(renamed_index_together_indexes) == 1:
                        renamed_index = renamed_index_together_indexes[0]
                        remove_from_added.append(renamed_index)
                        renamed_indexes.append(
                            (None, renamed_index.name, removed_index_together)
                        )
                        self.renamed_index_together_values[
                            index_together_app_label, index_together_model_name
                        ].append(removed_index_together)
            # Remove renamed indexes from the lists of added and removed
            # indexes.
            added_indexes = [
                idx for idx in added_indexes if idx not in remove_from_added
            ]
            removed_indexes = [
                idx for idx in removed_indexes if idx not in remove_from_removed
            ]

            self.altered_indexes.update(
                {
                    (app_label, model_name): {
                        "added_indexes": added_indexes,
                        "removed_indexes": removed_indexes,
                        "renamed_indexes": renamed_indexes,
                    }
                }
            )

    def generate_added_indexes(self):
        for (app_label, model_name), alt_indexes in self.altered_indexes.items():
            dependencies = self._get_dependencies_for_model(app_label, model_name)
            for index in alt_indexes["added_indexes"]:
                self.add_operation(
                    app_label,
                    operations.AddIndex(
                        model_name=model_name,
                        index=index,
                    ),
                    dependencies=dependencies,
                )

    def generate_removed_indexes(self):
        for (app_label, model_name), alt_indexes in self.altered_indexes.items():
            for index in alt_indexes["removed_indexes"]:
                self.add_operation(
                    app_label,
                    operations.RemoveIndex(
                        model_name=model_name,
                        name=index.name,
                    ),
                )

    def generate_renamed_indexes(self):
        for (app_label, model_name), alt_indexes in self.altered_indexes.items():
            for old_index_name, new_index_name, old_fields in alt_indexes[
                "renamed_indexes"
            ]:
                self.add_operation(
                    app_label,
                    operations.RenameIndex(
                        model_name=model_name,
                        new_name=new_index_name,
                        old_name=old_index_name,
                        old_fields=old_fields,
                    ),
                )

    def _constraint_should_be_dropped_and_recreated(
        self, old_constraint, new_constraint
    ):
        old_path, old_args, old_kwargs = old_constraint.deconstruct()
        new_path, new_args, new_kwargs = new_constraint.deconstruct()

        for attr in old_constraint.non_db_attrs:
            old_kwargs.pop(attr, None)
        for attr in new_constraint.non_db_attrs:
            new_kwargs.pop(attr, None)

        return (old_path, old_args, old_kwargs) != (new_path, new_args, new_kwargs)

    def create_altered_constraints(self):
        option_name = operations.AddConstraint.option_name
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]

            old_constraints = old_model_state.options[option_name]
            new_constraints = new_model_state.options[option_name]

            alt_constraints = []
            alt_constraints_name = []

            for old_c in old_constraints:
                for new_c in new_constraints:
                    old_c_dec = old_c.deconstruct()
                    new_c_dec = new_c.deconstruct()
                    if (
                        old_c_dec != new_c_dec
                        and old_c.name == new_c.name
                        and not self._constraint_should_be_dropped_and_recreated(
                            old_c, new_c
                        )
                    ):
                        alt_constraints.append(new_c)
                        alt_constraints_name.append(new_c.name)

            add_constraints = [
                c
                for c in new_constraints
                if c not in old_constraints and c.name not in alt_constraints_name
            ]
            rem_constraints = [
                c
                for c in old_constraints
                if c not in new_constraints and c.name not in alt_constraints_name
            ]

            self.altered_constraints.update(
                {
                    (app_label, model_name): {
                        "added_constraints": add_constraints,
                        "removed_constraints": rem_constraints,
                        "altered_constraints": alt_constraints,
                    }
                }
            )

    def generate_added_constraints(self):
        for (
            app_label,
            model_name,
        ), alt_constraints in self.altered_constraints.items():
            dependencies = self._get_dependencies_for_model(app_label, model_name)
            for constraint in alt_constraints["added_constraints"]:
                self.add_operation(
                    app_label,
                    operations.AddConstraint(
                        model_name=model_name,
                        constraint=constraint,
                    ),
                    dependencies=dependencies,
                )

    def generate_removed_constraints(self):
        for (
            app_label,
            model_name,
        ), alt_constraints in self.altered_constraints.items():
            for constraint in alt_constraints["removed_constraints"]:
                self.add_operation(
                    app_label,
                    operations.RemoveConstraint(
                        model_name=model_name,
                        name=constraint.name,
                    ),
                )

    def generate_altered_constraints(self):
        for (
            app_label,
            model_name,
        ), alt_constraints in self.altered_constraints.items():
            dependencies = self._get_dependencies_for_model(app_label, model_name)
            for constraint in alt_constraints["altered_constraints"]:
                self.add_operation(
                    app_label,
                    operations.AlterConstraint(
                        model_name=model_name,
                        name=constraint.name,
                        constraint=constraint,
                    ),
                    dependencies=dependencies,
                )

    @staticmethod
    def _get_dependencies_for_foreign_key(app_label, model_name, field, project_state):
        remote_field_model = None
        if hasattr(field.remote_field, "model"):
            remote_field_model = field.remote_field.model
        else:
            relations = project_state.relations[app_label, model_name]
            for (remote_app_label, remote_model_name), fields in relations.items():
                if any(
                    field == related_field.remote_field
                    for related_field in fields.values()
                ):
                    remote_field_model = f"{remote_app_label}.{remote_model_name}"
                    break
        # Account for FKs to swappable models
        swappable_setting = getattr(field, "swappable_setting", None)
        if swappable_setting is not None:
            dep_app_label = "__setting__"
            dep_object_name = swappable_setting
        else:
            dep_app_label, dep_object_name = resolve_relation(
                remote_field_model,
                app_label,
                model_name,
            )
        dependencies = [
            OperationDependency(
                dep_app_label, dep_object_name, None, OperationDependency.Type.CREATE
            )
        ]
        if getattr(field.remote_field, "through", None):
            through_app_label, through_object_name = resolve_relation(
                field.remote_field.through,
                app_label,
                model_name,
            )
            dependencies.append(
                OperationDependency(
                    through_app_label,
                    through_object_name,
                    None,
                    OperationDependency.Type.CREATE,
                )
            )
        return dependencies

    def _get_dependencies_for_generated_field(self, field):
        dependencies = []
        referenced_base_fields = models.Q(field.expression).referenced_base_fields
        newly_added_fields = sorted(self.new_field_keys - self.old_field_keys)
        for app_label, model_name, added_field_name in newly_added_fields:
            added_field = self.to_state.models[app_label, model_name].get_field(
                added_field_name
            )
            if (
                added_field.remote_field and added_field.remote_field.model
            ) or added_field.name in referenced_base_fields:
                dependencies.append(
                    OperationDependency(
                        app_label,
                        model_name,
                        added_field.name,
                        OperationDependency.Type.CREATE,
                    )
                )
        return dependencies

    def _get_dependencies_for_model(self, app_label, model_name):
        """Return foreign key dependencies of the given model."""
        dependencies = []
        model_state = self.to_state.models[app_label, model_name]
        for field in model_state.fields.values():
            if field.is_relation:
                dependencies.extend(
                    self._get_dependencies_for_foreign_key(
                        app_label,
                        model_name,
                        field,
                        self.to_state,
                    )
                )
        return dependencies

    def _get_altered_foo_together_operations(self, option_name):
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]

            # We run the old version through the field renames to account for those
            old_value = old_model_state.options.get(option_name)
            old_value = (
                {
                    tuple(
                        self.renamed_fields.get((app_label, model_name, n), n)
                        for n in unique
                    )
                    for unique in old_value
                }
                if old_value
                else set()
            )

            new_value = new_model_state.options.get(option_name)
            new_value = set(new_value) if new_value else set()

            if old_value != new_value:
                dependencies = []
                for foo_togethers in new_value:
                    for field_name in foo_togethers:
                        field = new_model_state.get_field(field_name)
                        if field.remote_field and field.remote_field.model:
                            dependencies.extend(
                                self._get_dependencies_for_foreign_key(
                                    app_label,
                                    model_name,
                                    field,
                                    self.to_state,
                                )
                            )
                yield (
                    old_value,
                    new_value,
                    app_label,
                    model_name,
                    dependencies,
                )

    def _generate_removed_altered_foo_together(self, operation):
        for (
            old_value,
            new_value,
            app_label,
            model_name,
            dependencies,
        ) in self._get_altered_foo_together_operations(operation.option_name):
            if operation == operations.AlterIndexTogether:
                old_value = {
                    value
                    for value in old_value
                    if value
                    not in self.renamed_index_together_values[app_label, model_name]
                }
            removal_value = new_value.intersection(old_value)
            if removal_value or old_value:
                self.add_operation(
                    app_label,
                    operation(
                        name=model_name, **{operation.option_name: removal_value}
                    ),
                    dependencies=dependencies,
                )

    def generate_removed_altered_unique_together(self):
        self._generate_removed_altered_foo_together(operations.AlterUniqueTogether)

    def _generate_altered_foo_together(self, operation):
        for (
            old_value,
            new_value,
            app_label,
            model_name,
            dependencies,
        ) in self._get_altered_foo_together_operations(operation.option_name):
            removal_value = new_value.intersection(old_value)
            if new_value != removal_value:
                self.add_operation(
                    app_label,
                    operation(name=model_name, **{operation.option_name: new_value}),
                    dependencies=dependencies,
                )

    def generate_altered_unique_together(self):
        self._generate_altered_foo_together(operations.AlterUniqueTogether)

    def generate_altered_db_table(self):
        models_to_check = self.kept_model_keys.union(
            self.kept_proxy_keys, self.kept_unmanaged_keys
        )
        for app_label, model_name in sorted(models_to_check):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            old_db_table_name = old_model_state.options.get("db_table")
            new_db_table_name = new_model_state.options.get("db_table")
            if old_db_table_name != new_db_table_name:
                self.add_operation(
                    app_label,
                    operations.AlterModelTable(
                        name=model_name,
                        table=new_db_table_name,
                    ),
                )

    def generate_altered_db_table_comment(self):
        models_to_check = self.kept_model_keys.union(
            self.kept_proxy_keys, self.kept_unmanaged_keys
        )
        for app_label, model_name in sorted(models_to_check):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]

            old_db_table_comment = old_model_state.options.get("db_table_comment")
            new_db_table_comment = new_model_state.options.get("db_table_comment")
            if old_db_table_comment != new_db_table_comment:
                self.add_operation(
                    app_label,
                    operations.AlterModelTableComment(
                        name=model_name,
                        table_comment=new_db_table_comment,
                    ),
                )

    def generate_altered_options(self):
        """
        Work out if any non-schema-affecting options have changed and make an
        operation to represent them in state changes (in case Python code in
        migrations needs them).
        """
        models_to_check = self.kept_model_keys.union(
            self.kept_proxy_keys,
            self.kept_unmanaged_keys,
            # unmanaged converted to managed
            self.old_unmanaged_keys & self.new_model_keys,
            # managed converted to unmanaged
            self.old_model_keys & self.new_unmanaged_keys,
        )

        for app_label, model_name in sorted(models_to_check):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            old_options = {
                key: value
                for key, value in old_model_state.options.items()
                if key in AlterModelOptions.ALTER_OPTION_KEYS
            }
            new_options = {
                key: value
                for key, value in new_model_state.options.items()
                if key in AlterModelOptions.ALTER_OPTION_KEYS
            }
            if old_options != new_options:
                self.add_operation(
                    app_label,
                    operations.AlterModelOptions(
                        name=model_name,
                        options=new_options,
                    ),
                )

    def generate_altered_order_with_respect_to(self):
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            if old_model_state.options.get(
                "order_with_respect_to"
            ) != new_model_state.options.get("order_with_respect_to"):
                # Make sure it comes second if we're adding
                # (removal dependency is part of RemoveField)
                dependencies = []
                if new_model_state.options.get("order_with_respect_to"):
                    dependencies.append(
                        OperationDependency(
                            app_label,
                            model_name,
                            new_model_state.options["order_with_respect_to"],
                            OperationDependency.Type.CREATE,
                        )
                    )
                # Actually generate the operation
                self.add_operation(
                    app_label,
                    operations.AlterOrderWithRespectTo(
                        name=model_name,
                        order_with_respect_to=new_model_state.options.get(
                            "order_with_respect_to"
                        ),
                    ),
                    dependencies=dependencies,
                )

    def generate_altered_managers(self):
        for app_label, model_name in sorted(self.kept_model_keys):
            old_model_name = self.renamed_models.get(
                (app_label, model_name), model_name
            )
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            if old_model_state.managers != new_model_state.managers:
                self.add_operation(
                    app_label,
                    operations.AlterModelManagers(
                        name=model_name,
                        managers=new_model_state.managers,
                    ),
                )

    def arrange_for_graph(self, changes, graph, migration_name=None):
        """
        Take a result from changes() and a MigrationGraph, and fix the names
        and dependencies of the changes so they extend the graph from the leaf
        nodes for each app.
        """
        leaves = graph.leaf_nodes()
        name_map = {}
        for app_label, migrations in list(changes.items()):
            if not migrations:
                continue
            # Find the app label's current leaf node
            app_leaf = None
            for leaf in leaves:
                if leaf[0] == app_label:
                    app_leaf = leaf
                    break
            # Do they want an initial migration for this app?
            if app_leaf is None and not self.questioner.ask_initial(app_label):
                # They don't.
                for migration in migrations:
                    name_map[(app_label, migration.name)] = (app_label, "__first__")
                del changes[app_label]
                continue
            # Work out the next number in the sequence
            if app_leaf is None:
                next_number = 1
            else:
                next_number = (self.parse_number(app_leaf[1]) or 0) + 1
            # Name each migration
            for i, migration in enumerate(migrations):
                if i == 0 and app_leaf:
                    migration.dependencies.append(app_leaf)
                new_name_parts = ["%04i" % next_number]
                if migration_name:
                    new_name_parts.append(migration_name)
                elif i == 0 and not app_leaf:
                    new_name_parts.append("initial")
                else:
                    new_name_parts.append(migration.suggest_name()[:100])
                new_name = "_".join(new_name_parts)
                name_map[(app_label, migration.name)] = (app_label, new_name)
                next_number += 1
                migration.name = new_name
        # Now fix dependencies
        for migrations in changes.values():
            for migration in migrations:
                migration.dependencies = [
                    name_map.get(d, d) for d in migration.dependencies
                ]
        return changes

    def _trim_to_apps(self, changes, app_labels):
        """
        Take changes from arrange_for_graph() and set of app labels, and return
        a modified set of changes which trims out as many migrations that are
        not in app_labels as possible. Note that some other migrations may
        still be present as they may be required dependencies.
        """
        # Gather other app dependencies in a first pass
        app_dependencies = {}
        for app_label, migrations in changes.items():
            for migration in migrations:
                for dep_app_label, name in migration.dependencies:
                    app_dependencies.setdefault(app_label, set()).add(dep_app_label)
        required_apps = set(app_labels)
        # Keep resolving till there's no change
        old_required_apps = None
        while old_required_apps != required_apps:
            old_required_apps = set(required_apps)
            required_apps.update(
                *[app_dependencies.get(app_label, ()) for app_label in required_apps]
            )
        # Remove all migrations that aren't needed
        for app_label in list(changes):
            if app_label not in required_apps:
                del changes[app_label]
        return changes

    @classmethod
    def parse_number(cls, name):
        """
        Given a migration name, try to extract a number from the beginning of
        it. For a squashed migration such as '0001_squashed_0004…', return the
        second number. If no number is found, return None.
        """
        if squashed_match := re.search(r".*_squashed_(\d+)", name):
            return int(squashed_match[1])
        match = re.match(r"^\d+", name)
        if match:
            return int(match[0])
        return None
