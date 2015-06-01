from __future__ import unicode_literals

from collections import OrderedDict

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

        This process is split in 3 phases:

        1. Group consecutive migrations with respect to a full plan on an empty
           database. The first migration of each group and all migrations that
           will later be unapplied are kept in mind for state preservation.
        2. We will iterate over the full plan and mutate the project state
           along the process. If the migration that will be mutated is one kept
           in mind from phase 1 the state right before that migration is
           stored.
           As soon as no migrations require preserving a state, the iteration
           over the full plan stops.
        3. During this step the migrations are applied
        """
        if plan is None:
            plan = self.migration_plan(targets)
        # Create the forwards plan Django would follow on an empty database
        full_plan = self.migration_plan(self.loader.graph.leaf_nodes(), clean_start=True)

        # Phase 1 -- Group successive migrations in plan.
        # Mapping of "migration -> position" in the full_plan
        node_map = {m: i for i, (m, _) in enumerate(full_plan)}
        groups = []
        # Mapping of "migration -> (position, backwards)" in the group
        current_group = OrderedDict()
        current_index = 0
        last = None
        compute_state_for = set()
        for migration, backwards in plan:
            if last is None:
                current_group[migration] = (0, backwards)
                compute_state_for.add(migration)
                current_index = 1
            else:
                if last[1] == backwards and (
                        backwards and node_map[last[0]] - 1 == node_map[migration] or
                        not backwards and node_map[last[0]] + 1 == node_map[migration]):
                    # If last and current node are both forwards or backwards
                    # AND if they are consecutive in the full_plan
                    current_group[migration] = (current_index, backwards)
                    if backwards:
                        compute_state_for.add(migration)
                    current_index += 1
                else:
                    groups.append(current_group)
                    current_group = OrderedDict()
                    current_group[migration] = (0, backwards)
                    compute_state_for.add(migration)
                    current_index = 1
            last = (migration, backwards)
        groups.append(current_group)

        # Phase 2 -- Compute and store project states. The migration that first
        # whose "before-state" is stored also triggers the rendering of
        # state.apps. From this time on models will be recursively reloaded as
        # explained in .state.get_related_models_recursive().
        states = {}
        state = ProjectState(real_apps=list(self.loader.unmigrated_apps))
        if self.progress_callback:
            self.progress_callback("render_start")
        for migration, _ in full_plan:
            if not compute_state_for:
                # The last migration that needs a preservation of its
                # "before-state" has been rendered.
                break
            do_run = migration in compute_state_for
            if do_run:
                if 'apps' not in state.__dict__:
                    state.apps  # Render all real_apps -- performance critical
                states[migration] = state.clone()
                compute_state_for.remove(migration)
            # Only preserve the state if the migration is being run later
            state = migration.mutate_state(state, preserve=do_run)
        if self.progress_callback:
            self.progress_callback("render_success")

        # Phase 3 -- Run the migrations from each group.
        for group in groups:
            migration, (_, backwards) = next(iter(group.items()))
            if not backwards:
                # We take the state from the first migration of the group and
                # reuse it for the other migrations in that group as
                # apply_migration() returns the new state.
                state = states[migration]
                for migration, (_, backwards) in group.items():
                    state = self.apply_migration(state, migration, fake=fake, fake_initial=fake_initial)
            else:
                # We cannot pass the state as with forwards migrations but have
                # to look it up for every migration.
                for migration, (_, backwards) in group.items():
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
