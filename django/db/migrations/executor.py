from django.apps.registry import apps as global_apps
from django.db import migrations, router

from .exceptions import InvalidMigrationPlan
from .loader import MigrationLoader
from .recorder import MigrationRecorder
from .state import ProjectState


class MigrationExecutor:
    """
    End-to-end migration execution - load migrations and run them up or down
    to a specified set of targets.
    """

    def __init__(self, connection, progress_callback=None):
        self.connection = connection
        self.loader = MigrationLoader(self.connection)
        self.recorder = MigrationRecorder(self.connection)
        self.progress_callback = progress_callback

    def migration_plan(self, targets, clean_start=False):
        """
        Given a set of targets, return a list of (Migration instance, backwards?).
        """
        plan = []
        if clean_start:
            applied = {}
        else:
            applied = dict(self.loader.applied_migrations)
        for target in targets:
            # If the target is (app_label, None), that means unmigrate everything
            if target[1] is None:
                for root in self.loader.graph.root_nodes():
                    if root[0] == target[0]:
                        for migration in self.loader.graph.backwards_plan(root):
                            if migration in applied:
                                plan.append((self.loader.graph.nodes[migration], True))
                                applied.pop(migration)
            # If the migration is already applied, do backwards mode,
            # otherwise do forwards mode.
            elif target in applied:
                # If the target is missing, it's likely a replaced migration.
                # Reload the graph without replacements.
                if (
                    self.loader.replace_migrations
                    and target not in self.loader.graph.node_map
                ):
                    self.loader.replace_migrations = False
                    self.loader.build_graph()
                    return self.migration_plan(targets, clean_start=clean_start)
                # Don't migrate backwards all the way to the target node (that
                # may roll back dependencies in other apps that don't need to
                # be rolled back); instead roll back through target's immediate
                # child(ren) in the same app, and no further.
                next_in_app = sorted(
                    n
                    for n in self.loader.graph.node_map[target].children
                    if n[0] == target[0]
                )
                for node in next_in_app:
                    for migration in self.loader.graph.backwards_plan(node):
                        if migration in applied:
                            plan.append((self.loader.graph.nodes[migration], True))
                            applied.pop(migration)
            else:
                for migration in self.loader.graph.forwards_plan(target):
                    if migration not in applied:
                        plan.append((self.loader.graph.nodes[migration], False))
                        applied[migration] = self.loader.graph.nodes[migration]
        return plan

    def _create_project_state(self, with_applied_migrations=False):
        """
        Create a project state including all the applications without
        migrations and applied migrations if with_applied_migrations=True.
        """
        state = ProjectState(real_apps=self.loader.unmigrated_apps)
        if with_applied_migrations:
            # Create the forwards plan Django would follow on an empty database
            full_plan = self.migration_plan(
                self.loader.graph.leaf_nodes(), clean_start=True
            )
            applied_migrations = {
                self.loader.graph.nodes[key]
                for key in self.loader.applied_migrations
                if key in self.loader.graph.nodes
            }
            for migration, _ in full_plan:
                if migration in applied_migrations:
                    migration.mutate_state(state, preserve=False)
        return state

    def migrate(self, targets, plan=None, state=None, fake=False, fake_initial=False):
        """
        Migrate the database up to the given targets.

        Django first needs to create all project states before a migration is
        (un)applied and in a second step run all the database operations.
        """
        # The django_migrations table must be present to record applied
        # migrations, but don't create it if there are no migrations to apply.
        if plan == []:
            if not self.recorder.has_table():
                return self._create_project_state(with_applied_migrations=False)
        else:
            self.recorder.ensure_schema()

        if plan is None:
            plan = self.migration_plan(targets)
        # Create the forwards plan Django would follow on an empty database
        full_plan = self.migration_plan(
            self.loader.graph.leaf_nodes(), clean_start=True
        )

        all_forwards = all(not backwards for mig, backwards in plan)
        all_backwards = all(backwards for mig, backwards in plan)

        if not plan:
            if state is None:
                # The resulting state should include applied migrations.
                state = self._create_project_state(with_applied_migrations=True)
        elif all_forwards == all_backwards:
            # This should only happen if there's a mixed plan
            raise InvalidMigrationPlan(
                "Migration plans with both forwards and backwards migrations "
                "are not supported. Please split your migration process into "
                "separate plans of only forwards OR backwards migrations.",
                plan,
            )
        elif all_forwards:
            if state is None:
                # The resulting state should still include applied migrations.
                state = self._create_project_state(with_applied_migrations=True)
            state = self._migrate_all_forwards(
                state, plan, full_plan, fake=fake, fake_initial=fake_initial
            )
        else:
            # No need to check for `elif all_backwards` here, as that condition
            # would always evaluate to true.
            state = self._migrate_all_backwards(plan, full_plan, fake=fake)

        self.check_replacements()

        return state

    def _migrate_all_forwards(self, state, plan, full_plan, fake, fake_initial):
        """
        Take a list of 2-tuples of the form (migration instance, False) and
        apply them in the order they occur in the full_plan.
        """
        migrations_to_run = {m[0] for m in plan}
        for migration, _ in full_plan:
            if not migrations_to_run:
                # We remove every migration that we applied from these sets so
                # that we can bail out once the last migration has been applied
                # and don't always run until the very end of the migration
                # process.
                break
            if migration in migrations_to_run:
                if "apps" not in state.__dict__:
                    if self.progress_callback:
                        self.progress_callback("render_start")
                    state.apps  # Render all -- performance critical
                    if self.progress_callback:
                        self.progress_callback("render_success")
                state = self.apply_migration(
                    state, migration, fake=fake, fake_initial=fake_initial
                )
                migrations_to_run.remove(migration)

        return state

    def _migrate_all_backwards(self, plan, full_plan, fake):
        """
        Take a list of 2-tuples of the form (migration instance, True) and
        unapply them in reverse order they occur in the full_plan.

        Since unapplying a migration requires the project state prior to that
        migration, Django will compute the migration states before each of them
        in a first run over the plan and then unapply them in a second run over
        the plan.
        """
        migrations_to_run = {m[0] for m in plan}
        # Holds all migration states prior to the migrations being unapplied
        states = {}
        state = self._create_project_state()
        applied_migrations = {
            self.loader.graph.nodes[key]
            for key in self.loader.applied_migrations
            if key in self.loader.graph.nodes
        }
        if self.progress_callback:
            self.progress_callback("render_start")
        for migration, _ in full_plan:
            if not migrations_to_run:
                # We remove every migration that we applied from this set so
                # that we can bail out once the last migration has been applied
                # and don't always run until the very end of the migration
                # process.
                break
            if migration in migrations_to_run:
                if "apps" not in state.__dict__:
                    state.apps  # Render all -- performance critical
                # The state before this migration
                states[migration] = state
                # The old state keeps as-is, we continue with the new state
                state = migration.mutate_state(state, preserve=True)
                migrations_to_run.remove(migration)
            elif migration in applied_migrations:
                # Only mutate the state if the migration is actually applied
                # to make sure the resulting state doesn't include changes
                # from unrelated migrations.
                migration.mutate_state(state, preserve=False)
        if self.progress_callback:
            self.progress_callback("render_success")

        for migration, _ in plan:
            self.unapply_migration(states[migration], migration, fake=fake)
            applied_migrations.remove(migration)

        # Generate the post migration state by starting from the state before
        # the last migration is unapplied and mutating it to include all the
        # remaining applied migrations.
        last_unapplied_migration = plan[-1][0]
        state = states[last_unapplied_migration]
        # Avoid mutating state with apps rendered as it's an expensive
        # operation.
        del state.apps
        for index, (migration, _) in enumerate(full_plan):
            if migration == last_unapplied_migration:
                for migration, _ in full_plan[index:]:
                    if migration in applied_migrations:
                        migration.mutate_state(state, preserve=False)
                break

        return state

    def apply_migration(self, state, migration, fake=False, fake_initial=False):
        """Run a migration forwards."""
        migration_recorded = False
        if self.progress_callback:
            self.progress_callback("apply_start", migration, fake)
        if not fake:
            if fake_initial:
                # Test to see if this is an already-applied initial migration
                applied, state = self.detect_soft_applied(state, migration)
                if applied:
                    fake = True
            if not fake:
                # Alright, do it normally
                with self.connection.schema_editor(
                    atomic=migration.atomic
                ) as schema_editor:
                    state = migration.apply(state, schema_editor)
                    if not schema_editor.deferred_sql:
                        self.record_migration(migration.app_label, migration.name)
                        migration_recorded = True
        if not migration_recorded:
            self.record_migration(migration.app_label, migration.name)
        # Report progress
        if self.progress_callback:
            self.progress_callback("apply_success", migration, fake)
        return state

    def record_migration(self, app_label, name, forward=True):
        migration = self.loader.disk_migrations.get((app_label, name))
        # For replacement migrations, record individual statuses
        if migration and migration.replaces:
            for replaced_app_label, replaced_name in migration.replaces:
                self.record_migration(replaced_app_label, replaced_name, forward)
        if forward:
            self.recorder.record_applied(app_label, name)
        else:
            self.recorder.record_unapplied(app_label, name)

    def unapply_migration(self, state, migration, fake=False):
        """Run a migration backwards."""
        if self.progress_callback:
            self.progress_callback("unapply_start", migration, fake)
        if not fake:
            with self.connection.schema_editor(
                atomic=migration.atomic
            ) as schema_editor:
                state = migration.unapply(state, schema_editor)
        self.record_migration(migration.app_label, migration.name, forward=False)
        # Report progress
        if self.progress_callback:
            self.progress_callback("unapply_success", migration, fake)
        return state

    def check_replacements(self):
        """
        Mark replacement migrations applied if their replaced set all are.

        Do this unconditionally on every migrate, rather than just when
        migrations are applied or unapplied, to correctly handle the case
        when a new squash migration is pushed to a deployment that already had
        all its replaced migrations applied. In this case no new migration will
        be applied, but the applied state of the squashed migration must be
        maintained.
        """
        applied = self.recorder.applied_migrations()
        for key, migration in self.loader.replacements.items():
            all_applied = all(m in applied for m in migration.replaces)
            if all_applied and key not in applied:
                self.recorder.record_applied(*key)

    def detect_soft_applied(self, project_state, migration):
        """
        Test whether a migration has been implicitly applied - that the
        tables or columns it would create exist. This is intended only for use
        on initial migrations (as it only looks for CreateModel and AddField).
        """

        def should_skip_detecting_model(migration, model):
            """
            No need to detect tables for proxy models, unmanaged models, or
            models that can't be migrated on the current database.
            """
            return (
                model._meta.proxy
                or not model._meta.managed
                or not router.allow_migrate(
                    self.connection.alias,
                    migration.app_label,
                    model_name=model._meta.model_name,
                )
            )

        if migration.initial is None:
            # Bail if the migration isn't the first one in its app
            if any(app == migration.app_label for app, name in migration.dependencies):
                return False, project_state
        elif migration.initial is False:
            # Bail if it's NOT an initial migration
            return False, project_state

        if project_state is None:
            after_state = self.loader.project_state(
                (migration.app_label, migration.name), at_end=True
            )
        else:
            after_state = migration.mutate_state(project_state)
        apps = after_state.apps
        found_create_model_migration = False
        found_add_field_migration = False
        fold_identifier_case = self.connection.features.ignores_table_name_case
        with self.connection.cursor() as cursor:
            existing_table_names = set(
                self.connection.introspection.table_names(cursor)
            )
            if fold_identifier_case:
                existing_table_names = {
                    name.casefold() for name in existing_table_names
                }
        # Make sure all create model and add field operations are done
        for operation in migration.operations:
            if isinstance(operation, migrations.CreateModel):
                model = apps.get_model(migration.app_label, operation.name)
                if model._meta.swapped:
                    # We have to fetch the model to test with from the
                    # main app cache, as it's not a direct dependency.
                    model = global_apps.get_model(model._meta.swapped)
                if should_skip_detecting_model(migration, model):
                    continue
                db_table = model._meta.db_table
                if fold_identifier_case:
                    db_table = db_table.casefold()
                if db_table not in existing_table_names:
                    return False, project_state
                found_create_model_migration = True
            elif isinstance(operation, migrations.AddField):
                model = apps.get_model(migration.app_label, operation.model_name)
                if model._meta.swapped:
                    # We have to fetch the model to test with from the
                    # main app cache, as it's not a direct dependency.
                    model = global_apps.get_model(model._meta.swapped)
                if should_skip_detecting_model(migration, model):
                    continue

                table = model._meta.db_table
                field = model._meta.get_field(operation.name)

                # Handle implicit many-to-many tables created by AddField.
                if field.many_to_many:
                    through_db_table = field.remote_field.through._meta.db_table
                    if fold_identifier_case:
                        through_db_table = through_db_table.casefold()
                    if through_db_table not in existing_table_names:
                        return False, project_state
                    else:
                        found_add_field_migration = True
                        continue
                with self.connection.cursor() as cursor:
                    columns = self.connection.introspection.get_table_description(
                        cursor, table
                    )
                for column in columns:
                    field_column = field.column
                    column_name = column.name
                    if fold_identifier_case:
                        column_name = column_name.casefold()
                        field_column = field_column.casefold()
                    if column_name == field_column:
                        found_add_field_migration = True
                        break
                else:
                    return False, project_state
        # If we get this far and we found at least one CreateModel or AddField
        # migration, the migration is considered implicitly applied.
        return (found_create_model_migration or found_add_field_migration), after_state
