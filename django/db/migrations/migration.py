from django.core.management.sql import emit_post_operation_signal
from django.db.migrations.utils import get_migration_name_timestamp
from django.db.transaction import atomic

from .exceptions import IrreversibleError


class Migration:
    """
    The base class for all migrations.

    Migration files will import this from django.db.migrations.Migration
    and subclass it as a class called Migration. It will have one or more
    of the following attributes:

     - operations: A list of Operation instances, probably from django.db.migrations.operations
     - dependencies: A list of tuples of (app_path, migration_name)
     - run_before: A list of tuples of (app_path, migration_name)
     - replaces: A list of migration_names

    Note that all migrations come out of migrations and into the Loader or
    Graph as instances, having been initialized with their app label and name.
    """

    APPLY_RECURSION_ERROR_MESSAGE = (
        "A cycle in the post_operation signal's chain has caused infinite recursion."
    )

    # Operations to apply during this migration, in order.
    operations = []

    # Other migrations that should be run before this migration.
    # Should be a list of (app, migration_name).
    dependencies = []

    # Other migrations that should be run after this one (i.e. have
    # this migration added to their dependencies). Useful to make third-party
    # apps' migrations run after your AUTH_USER replacement, for example.
    run_before = []

    # Migration names in this app that this migration replaces. If this is
    # non-empty, this migration will only be applied if all these migrations
    # are not applied.
    replaces = []

    # Is this an initial migration? Initial migrations are skipped on
    # --fake-initial if the table or fields already exist. If None, check if
    # the migration has any dependencies to determine if there are dependencies
    # to tell if db introspection needs to be done. If True, always perform
    # introspection. If False, never perform introspection.
    initial = None

    # Whether to wrap the whole migration in a transaction. Only has an effect
    # on database backends which support transactional DDL.
    atomic = True

    def __init__(self, name, app_label):
        self.name = name
        self.app_label = app_label
        # Copy dependencies & other attrs as we might mutate them at runtime
        self.operations = list(self.__class__.operations)
        self.dependencies = list(self.__class__.dependencies)
        self.run_before = list(self.__class__.run_before)
        self.replaces = list(self.__class__.replaces)

    def __eq__(self, other):
        return (
            isinstance(other, Migration) and
            self.name == other.name and
            self.app_label == other.app_label
        )

    def __repr__(self):
        return "<Migration %s.%s>" % (self.app_label, self.name)

    def __str__(self):
        return "%s.%s" % (self.app_label, self.name)

    def __hash__(self):
        return hash("%s.%s" % (self.app_label, self.name))

    def mutate_state(self, project_state, preserve=True):
        """
        Take a ProjectState and return a new one with the migration's
        operations applied to it. Preserve the original object state by
        default and return a mutated state from a copy.
        """
        new_state = project_state
        if preserve:
            new_state = project_state.clone()

        for operation in self.operations:
            operation.state_forwards(self.app_label, new_state)
        return new_state

    def _apply_operation(self, project_state, schema_editor, collect_sql, operation):
        # Save the state before the operation has run
        from_state = project_state.clone()
        to_state = project_state

        # If this operation cannot be represented as SQL, place a comment
        # there instead
        if collect_sql:
            schema_editor.collected_sql.append("--")
            if not operation.reduces_to_sql:
                schema_editor.collected_sql.append(
                    "-- MIGRATION NOW PERFORMS OPERATION THAT CANNOT BE WRITTEN AS SQL:"
                )
            schema_editor.collected_sql.append("-- %s" % operation.describe())
            schema_editor.collected_sql.append("--")
            if not operation.reduces_to_sql:
                return (from_state, to_state)
        operation.state_forwards(self.app_label, to_state)
        # Run the operation
        atomic_operation = operation.atomic or (self.atomic and operation.atomic is not False)
        if not schema_editor.atomic_migration and atomic_operation:
            # Force a transaction on a non-transactional-DDL backend or an
            # atomic operation inside a non-atomic migration.
            with atomic(schema_editor.connection.alias):
                operation.database_forwards(self.app_label, schema_editor, from_state, to_state)
        else:
            # Normal behaviour
            operation.database_forwards(self.app_label, schema_editor, from_state, to_state)
        return (from_state, to_state)

    def _apply_operations(
        self,
        project_state,
        schema_editor,
        collect_sql,
        operations,
        root_operation=None,
    ):
        if not operations:
            return

        for operation in operations:
            from_state, to_state = self._apply_operation(project_state, schema_editor, collect_sql, operation)
            path_root_operation = root_operation if root_operation else operation
            injected_operations = emit_post_operation_signal(
                migration=self,
                operation=operation,
                from_state=from_state.clone(),
                to_state=to_state.clone(),
                root_operation=path_root_operation,
            )
            self._apply_operations(project_state, schema_editor, collect_sql, injected_operations, path_root_operation)

    def apply(self, project_state, schema_editor, collect_sql=False):
        """
        Take a project_state representing all migrations prior to this one
        and a schema_editor for a live database and apply the migration
        in a forwards order.

        For each operation, emit a post_operation signal and collect the
        injected operations to be applied recursively using an in-order
        traversal (LNR) approach.

        Return the resulting project state for efficient reuse by following
        Migrations.
        """
        try:
            self._apply_operations(project_state, schema_editor, collect_sql, self.operations)
        except RecursionError:
            raise RecursionError(Migration.APPLY_RECURSION_ERROR_MESSAGE)

        return project_state

    def _unapply_operations(self, to_state, operations, root_operation=None):
        to_run = []
        if not operations:
            return to_run

        for operation in operations:
            # If it's irreversible, error out
            if not operation.reversible:
                raise IrreversibleError("Operation %s in %s is not reversible" % (operation, self))
            # Preserve new state from previous run to not tamper the same state
            # over all operations
            to_state = to_state.clone()
            from_state = to_state.clone()
            operation.state_forwards(self.app_label, to_state)
            to_run.insert(0, (operation, from_state, to_state))

            # Insert injected operations from post_operation signal receivers.
            path_root_operation = root_operation if root_operation else operation
            injected_operations = emit_post_operation_signal(
                migration=self,
                operation=operation,
                from_state=from_state.clone(),
                to_state=to_state.clone(),
                root_operation=path_root_operation,
            )

            for operation_to_run in reversed(
                self._unapply_operations(to_state, injected_operations, path_root_operation)
            ):
                to_run.insert(0, operation_to_run)

        return to_run

    def unapply(self, project_state, schema_editor, collect_sql=False):
        """
        Take a project_state representing all migrations prior to this one
        and a schema_editor for a live database and apply the migration
        in a reverse order.

        For each operation, the injected operations from post_operation signal
        receivers are collected recursively, using an in-order traversal (LNR)
        approach.

        The backwards migration process consists of two phases:

        1. The intermediate states from right before the first until right
           after the last operation inside this migration are preserved.
        2. The operations are applied in reverse order using the states
           recorded in step 1.
        """
        # Phase 1
        try:
            # Construct all the intermediate states we need for a reverse migration
            to_run = self._unapply_operations(project_state, self.operations)
        except RecursionError:
            raise RecursionError(Migration.APPLY_RECURSION_ERROR_MESSAGE)

        # Phase 2
        for operation, to_state, from_state in to_run:
            if collect_sql:
                schema_editor.collected_sql.append("--")
                if not operation.reduces_to_sql:
                    schema_editor.collected_sql.append(
                        "-- MIGRATION NOW PERFORMS OPERATION THAT CANNOT BE WRITTEN AS SQL:"
                    )
                schema_editor.collected_sql.append("-- %s" % operation.describe())
                schema_editor.collected_sql.append("--")
                if not operation.reduces_to_sql:
                    continue
            atomic_operation = operation.atomic or (self.atomic and operation.atomic is not False)
            if not schema_editor.atomic_migration and atomic_operation:
                # Force a transaction on a non-transactional-DDL backend or an
                # atomic operation inside a non-atomic migration.
                with atomic(schema_editor.connection.alias):
                    operation.database_backwards(self.app_label, schema_editor, from_state, to_state)
            else:
                # Normal behaviour
                operation.database_backwards(self.app_label, schema_editor, from_state, to_state)
        return project_state

    def suggest_name(self):
        """
        Suggest a name for the operations this migration might represent. Names
        are not guaranteed to be unique, but put some effort into the fallback
        name to avoid VCS conflicts if possible.
        """
        if self.initial:
            return 'initial'

        raw_fragments = [op.migration_name_fragment for op in self.operations]
        fragments = [name for name in raw_fragments if name]

        if not fragments or len(fragments) != len(self.operations):
            return 'auto_%s' % get_migration_name_timestamp()

        name = fragments[0]
        for fragment in fragments[1:]:
            new_name = f'{name}_{fragment}'
            if len(new_name) > 52:
                name = f'{name}_and_more'
                break
            name = new_name
        return name


class SwappableTuple(tuple):
    """
    Subclass of tuple so Django can tell this was originally a swappable
    dependency when it reads the migration file.
    """

    def __new__(cls, value, setting):
        self = tuple.__new__(cls, value)
        self.setting = setting
        return self


def swappable_dependency(value):
    """Turn a setting value into a dependency."""
    return SwappableTuple((value.split(".", 1)[0], "__first__"), value)
