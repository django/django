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
        self.loader.load_disk()
        self.recorder = MigrationRecorder(self.connection)
        self.progress_callback = progress_callback

    def migration_plan(self, targets):
        """
        Given a set of targets, returns a list of (Migration instance, backwards?).
        """
        plan = []
        applied = self.recorder.applied_migrations()
        for target in targets:
            # If the target is (appname, None), that means unmigrate everything
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
                project_state = self.loader.graph.project_state((migration.app_label, migration.name), at_end=False)
                if not backwards:
                    migration.apply(project_state, schema_editor)
                else:
                    migration.unapply(project_state, schema_editor)
                statements.extend(schema_editor.collected_sql)
        return statements

    def apply_migration(self, migration, fake=False):
        """
        Runs a migration forwards.
        """
        if self.progress_callback:
            self.progress_callback("apply_start", migration)
        if not fake:
            with self.connection.schema_editor() as schema_editor:
                project_state = self.loader.graph.project_state((migration.app_label, migration.name), at_end=False)
                migration.apply(project_state, schema_editor)
        self.recorder.record_applied(migration.app_label, migration.name)
        if self.progress_callback:
            self.progress_callback("apply_success", migration)

    def unapply_migration(self, migration, fake=False):
        """
        Runs a migration backwards.
        """
        if self.progress_callback:
            self.progress_callback("unapply_start", migration)
        if not fake:
            with self.connection.schema_editor() as schema_editor:
                project_state = self.loader.graph.project_state((migration.app_label, migration.name), at_end=False)
                migration.unapply(project_state, schema_editor)
        self.recorder.record_unapplied(migration.app_label, migration.name)
        if self.progress_callback:
            self.progress_callback("unapply_success", migration)
