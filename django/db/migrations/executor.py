from __future__ import unicode_literals

from django.db import migrations
from django.apps.registry import apps as global_apps
from .loader import MigrationLoader
from .recorder import MigrationRecorder


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

    def migration_plan(self, targets):
        """
        Given a set of targets, returns a list of (Migration instance, backwards?).
        """
        plan = []
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
                backwards_plan = self.loader.graph.backwards_plan(target)[:-1]
                # We only do this if the migration is not the most recent one
                # in its app - that is, another migration with the same app
                # label is in the backwards plan
                if any(node[0] == target[0] for node in backwards_plan):
                    for migration in backwards_plan:
                        if migration in applied:
                            plan.append((self.loader.graph.nodes[migration], True))
                            applied.remove(migration)
            else:
                for migration in self.loader.graph.forwards_plan(target):
                    if migration not in applied:
                        plan.append((self.loader.graph.nodes[migration], False))
                        applied.add(migration)
        return plan

    def migrate(self, targets, plan=None, fake=False):
        """
        Migrates the database up to the given targets.
        """
        if plan is None:
            plan = self.migration_plan(targets)
        for migration, backwards in plan:
            if not backwards:
                self.apply_migration(migration, fake=fake)
            else:
                self.unapply_migration(migration, fake=fake)

    def collect_sql(self, plan):
        """
        Takes a migration plan and returns a list of collected SQL
        statements that represent the best-efforts version of that plan.
        """
        statements = []
        for migration, backwards in plan:
            with self.connection.schema_editor(collect_sql=True) as schema_editor:
                project_state = self.loader.project_state((migration.app_label, migration.name), at_end=False)
                if not backwards:
                    migration.apply(project_state, schema_editor, collect_sql=True)
                else:
                    migration.unapply(project_state, schema_editor, collect_sql=True)
            statements.extend(schema_editor.collected_sql)
        return statements

    def apply_migration(self, migration, fake=False):
        """
        Runs a migration forwards.
        """
        if self.progress_callback:
            self.progress_callback("apply_start", migration, fake)
        if not fake:
            # Test to see if this is an already-applied initial migration
            if self.detect_soft_applied(migration):
                fake = True
            else:
                # Alright, do it normally
                with self.connection.schema_editor() as schema_editor:
                    project_state = self.loader.project_state((migration.app_label, migration.name), at_end=False)
                    migration.apply(project_state, schema_editor)
        # For replacement migrations, record individual statuses
        if migration.replaces:
            for app_label, name in migration.replaces:
                self.recorder.record_applied(app_label, name)
        else:
            self.recorder.record_applied(migration.app_label, migration.name)
        # Report progress
        if self.progress_callback:
            self.progress_callback("apply_success", migration, fake)

    def unapply_migration(self, migration, fake=False):
        """
        Runs a migration backwards.
        """
        if self.progress_callback:
            self.progress_callback("unapply_start", migration, fake)
        if not fake:
            with self.connection.schema_editor() as schema_editor:
                project_state = self.loader.project_state((migration.app_label, migration.name), at_end=False)
                migration.unapply(project_state, schema_editor)
        # For replacement migrations, record individual statuses
        if migration.replaces:
            for app_label, name in migration.replaces:
                self.recorder.record_unapplied(app_label, name)
        else:
            self.recorder.record_unapplied(migration.app_label, migration.name)
        # Report progress
        if self.progress_callback:
            self.progress_callback("unapply_success", migration, fake)

    def detect_soft_applied(self, migration):
        """
        Tests whether a migration has been implicitly applied - that the
        tables it would create exist. This is intended only for use
        on initial migrations (as it only looks for CreateModel).
        """
        project_state = self.loader.project_state((migration.app_label, migration.name), at_end=True)
        apps = project_state.render()
        found_create_migration = False
        # Bail if the migration isn't the first one in its app
        if [name for app, name in migration.dependencies if app == migration.app_label]:
            return False
        # Make sure all create model are done
        for operation in migration.operations:
            if isinstance(operation, migrations.CreateModel):
                model = apps.get_model(migration.app_label, operation.name)
                if model._meta.swapped:
                    # We have to fetch the model to test with from the
                    # main app cache, as it's not a direct dependency.
                    model = global_apps.get_model(model._meta.swapped)
                if model._meta.db_table not in self.connection.introspection.get_table_list(self.connection.cursor()):
                    return False
                found_create_migration = True
        # If we get this far and we found at least one CreateModel migration,
        # the migration is considered implicitly applied.
        return found_create_migration
