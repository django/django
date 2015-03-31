from __future__ import unicode_literals

from django.apps.registry import apps as global_apps
from django.db import migrations

from .loader import MigrationLoader
from .recorder import MigrationRecorder
from .state import ProjectState


class MigrationExecutor(object):
    """
    End-to-end migration execution - loads migrations, and runs them
    up or down to a specified set of targets.
    """

    def __init__(self, connection, progress_callback=None):
        self.connection = connection
        self.loader = MigrationLoader(self.connection)
        self.recorder = MigrationRecorder(self.connection)
        self.progress_callback = progress_callback

    def migration_plan(self, targets, clean_start=False):
        """
        Given a set of targets, returns a list of (Migration instance, backwards?).
        """
        plan = []
        if clean_start:
            applied = set()
        else:
            applied = set(self.loader.applied_migrations)
        for target in targets:
            # If the target is (app_label, None), that means unmigrate everything
            if target[1] is None:
                for root in self.loader.graph.root_nodes():
                    if root[0] == target[0]:
                        for migration in self.loader.graph.backwards_plan(root):
                            if migration in applied:
                                plan.append((self.loader.graph.nodes[migration], True))
                                applied.remove(migration)
            # If the migration is already applied, do backwards mode,
            # otherwise do forwards mode.
            elif target in applied:
                # Don't migrate backwards all the way to the target node (that
                # may roll back dependencies in other apps that don't need to
                # be rolled back); instead roll back through target's immediate
                # child(ren) in the same app, and no further.
                next_in_app = sorted(
                    n for n in
                    self.loader.graph.node_map[target].children
                    if n[0] == target[0]
                )
                for node in next_in_app:
                    for migration in self.loader.graph.backwards_plan(node):
                        if migration in applied:
                            plan.append((self.loader.graph.nodes[migration], True))
                            applied.remove(migration)
            else:
                for migration in self.loader.graph.forwards_plan(target):
                    if migration not in applied:
                        plan.append((self.loader.graph.nodes[migration], False))
                        applied.add(migration)
        return plan

    def migrate(self, targets, plan=None, fake=False, fake_initial=False):
        """
        Migrates the database up to the given targets.

        Django first needs to create all project states before a migration is
        (un)applied and in a second step run all the database operations.
        """
        if plan is None:
            plan = self.migration_plan(targets)
        migrations_to_run = {m[0] for m in plan}
        # Create the forwards plan Django would follow on an empty database
        full_plan = self.migration_plan(self.loader.graph.leaf_nodes(), clean_start=True)
        # Holds all states right before a migration is applied
        # if the migration is being run.
        states = {}
        state = ProjectState(real_apps=list(self.loader.unmigrated_apps))
        if self.progress_callback:
            self.progress_callback("render_start")
        # Phase 1 -- Store all project states of migrations right before they
        # are applied. The first migration that will be applied in phase 2 will
        # trigger the rendering of the initial project state. From this time on
        # models will be recursively reloaded as explained in
        # `django.db.migrations.state.get_related_models_recursive()`.
        for migration, _ in full_plan:
            if not migrations_to_run:
                # We remove every migration whose state was already computed
                # from the set below (`migrations_to_run.remove(migration)`).
                # If no states for migrations must be computed, we can exit
                # this loop. Migrations that occur after the latest migration
                # that is about to be applied would only trigger unneeded
                # mutate_state() calls.
                break
            do_run = migration in migrations_to_run
            if do_run:
                if 'apps' not in state.__dict__:
                    state.apps  # Render all real_apps -- performance critical
                states[migration] = state.clone()
                migrations_to_run.remove(migration)
            # Only preserve the state if the migration is being run later
            state = migration.mutate_state(state, preserve=do_run)
        if self.progress_callback:
            self.progress_callback("render_success")
        # Phase 2 -- Run the migrations
        for migration, backwards in plan:
            if not backwards:
                self.apply_migration(states[migration], migration, fake=fake, fake_initial=fake_initial)
            else:
                self.unapply_migration(states[migration], migration, fake=fake)

    def collect_sql(self, plan):
        """
        Takes a migration plan and returns a list of collected SQL
        statements that represent the best-efforts version of that plan.
        """
        statements = []
        state = None
        for migration, backwards in plan:
            with self.connection.schema_editor(collect_sql=True) as schema_editor:
                if state is None:
                    state = self.loader.project_state((migration.app_label, migration.name), at_end=False)
                if not backwards:
                    state = migration.apply(state, schema_editor, collect_sql=True)
                else:
                    state = migration.unapply(state, schema_editor, collect_sql=True)
            statements.extend(schema_editor.collected_sql)
        return statements

    def apply_migration(self, state, migration, fake=False, fake_initial=False):
        """
        Runs a migration forwards.
        """
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
                with self.connection.schema_editor() as schema_editor:
                    state = migration.apply(state, schema_editor)
        # For replacement migrations, record individual statuses
        if migration.replaces:
            for app_label, name in migration.replaces:
                self.recorder.record_applied(app_label, name)
        else:
            self.recorder.record_applied(migration.app_label, migration.name)
        # Report progress
        if self.progress_callback:
            self.progress_callback("apply_success", migration, fake)
        return state

    def unapply_migration(self, state, migration, fake=False):
        """
        Runs a migration backwards.
        """
        if self.progress_callback:
            self.progress_callback("unapply_start", migration, fake)
        if not fake:
            with self.connection.schema_editor() as schema_editor:
                state = migration.unapply(state, schema_editor)
        # For replacement migrations, record individual statuses
        if migration.replaces:
            for app_label, name in migration.replaces:
                self.recorder.record_unapplied(app_label, name)
        else:
            self.recorder.record_unapplied(migration.app_label, migration.name)
        # Report progress
        if self.progress_callback:
            self.progress_callback("unapply_success", migration, fake)
        return state

    def detect_soft_applied(self, project_state, migration):
        """
        Tests whether a migration has been implicitly applied - that the
        tables it would create exist. This is intended only for use
        on initial migrations (as it only looks for CreateModel).
        """
        # Bail if the migration isn't the first one in its app
        if [name for app, name in migration.dependencies if app == migration.app_label]:
            return False, project_state
        if project_state is None:
            after_state = self.loader.project_state((migration.app_label, migration.name), at_end=True)
        else:
            after_state = migration.mutate_state(project_state)
        apps = after_state.apps
        found_create_migration = False
        # Make sure all create model are done
        for operation in migration.operations:
            if isinstance(operation, migrations.CreateModel):
                model = apps.get_model(migration.app_label, operation.name)
                if model._meta.swapped:
                    # We have to fetch the model to test with from the
                    # main app cache, as it's not a direct dependency.
                    model = global_apps.get_model(model._meta.swapped)
                if model._meta.db_table not in self.connection.introspection.table_names(self.connection.cursor()):
                    return False, project_state
                found_create_migration = True
        # If we get this far and we found at least one CreateModel migration,
        # the migration is considered implicitly applied.
        return found_create_migration, after_state
