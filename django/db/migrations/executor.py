from .loader import MigrationLoader
from .recorder import MigrationRecorder


class MigrationExecutor(object):
    """
    End-to-end migration execution - loads migrations, and runs them
    up or down to a specified set of targets.
    """

    def __init__(self, connection):
        self.connection = connection
        self.loader = MigrationLoader(self.connection)
        self.recorder = MigrationRecorder(self.connection)

    def migration_plan(self, targets):
        """
        Given a set of targets, returns a list of (Migration instance, backwards?).
        """
        plan = []
        applied = self.recorder.applied_migrations()
        for target in targets:
            # If the migration is already applied, do backwards mode,
            # otherwise do forwards mode.
            if target in applied:
                for migration in self.loader.graph.backwards_plan(target)[:-1]:
                    if migration in applied:
                        plan.append((self.loader.graph.nodes[migration], True))
                        applied.remove(migration)
            else:
                for migration in self.loader.graph.forwards_plan(target):
                    if migration not in applied:
                        plan.append((self.loader.graph.nodes[migration], False))
                        applied.add(migration)
        return plan

    def migrate(self, targets):
        """
        Migrates the database up to the given targets.
        """
        plan = self.migration_plan(targets)
        for migration, backwards in plan:
            if not backwards:
                self.apply_migration(migration)
            else:
                self.unapply_migration(migration)

    def apply_migration(self, migration):
        """
        Runs a migration forwards.
        """
        with self.connection.schema_editor() as schema_editor:
            project_state = self.loader.graph.project_state((migration.app_label, migration.name), at_end=False)
            migration.apply(project_state, schema_editor)
        self.recorder.record_applied(migration.app_label, migration.name)

    def unapply_migration(self, migration):
        """
        Runs a migration backwards.
        """
        with self.connection.schema_editor() as schema_editor:
            project_state = self.loader.graph.project_state((migration.app_label, migration.name), at_end=False)
            migration.unapply(project_state, schema_editor)
        self.recorder.record_unapplied(migration.app_label, migration.name)
