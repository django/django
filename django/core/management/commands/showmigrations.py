import sys
from enum import StrEnum

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class MigrationStatus(StrEnum):
    """
    ``status`` field on each row returned by :meth:`Command.get_migration_data`.

    Members subclass :class:`str`, so they compare equal to their string values
    and serialize like plain strings.

    * :attr:`APPLIED` — Recorded in ``django_migrations`` for this migration name
      and reflected in the loader's applied set (``[X]`` in the default list
      output).
    * :attr:`UNRECORDED` — The loader treats this migration as applied (e.g. all
      replaced migrations of a squash are recorded), but there is no row yet for
      this migration name in ``django_migrations`` (``[-]`` and the "finish
      recording" hint).
    * :attr:`UNAPPLIED` — Not applied (``[ ]`` in the default list output).
    """

    APPLIED = "applied"
    UNRECORDED = "unrecorded"
    UNAPPLIED = "unapplied"


class Command(BaseCommand):
    help = "Shows all available migrations for the current project"

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            nargs="*",
            help="App labels of applications to limit the output to.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=tuple(connections),
            help=(
                "Nominates a database to show migrations for. Defaults to the "
                '"default" database.'
            ),
        )

        formats = parser.add_mutually_exclusive_group()
        formats.add_argument(
            "--list",
            "-l",
            action="store_const",
            dest="format",
            const="list",
            help=(
                "Shows a list of all migrations and which are applied. "
                "With a verbosity level of 2 or above, the applied datetimes "
                "will be included."
            ),
        )
        formats.add_argument(
            "--plan",
            "-p",
            action="store_const",
            dest="format",
            const="plan",
            help=(
                "Shows all migrations in the order they will be applied. With a "
                "verbosity level of 2 or above all direct migration dependencies and "
                "reverse dependencies (run_before) will be included."
            ),
        )

        parser.set_defaults(format="list")

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]

        # Get the database we're operating from
        db = options["database"]
        connection = connections[db]

        plan = options["format"] == "plan"
        rows = self.get_migration_data(
            connection, app_names=options["app_label"], plan=plan
        )
        return self.show_plan(rows) if plan else self.show_list(rows)

    def _validate_app_names(self, loader, app_names):
        has_bad_names = False
        for app_name in app_names:
            try:
                apps.get_app_config(app_name)
            except LookupError as err:
                self.stderr.write(str(err))
                has_bad_names = True
        if has_bad_names:
            sys.exit(2)

    def _migration_row(
        self,
        *,
        app,
        name,
        title,
        status,
        applied_at,
    ):
        return {
            "app": app,
            "name": name,
            "title": title,
            "status": status,
            "applied_at": applied_at,
        }

    def get_migration_data(self, connection, *, app_names=None, plan=False):
        """
        Return a list of dicts describing migrations for list or plan output.

        Each row includes ``app``, ``name``, ``title``, ``status``, and
        ``applied_at``. Use ``plan=False`` (the default) for per-app list ordering;
        use ``plan=True`` for global apply order as in ``showmigrations --plan``,
        in which case each row also has ``dependency_labels`` (list of
        ``app.name`` dependency strings). List mode may include a placeholder row
        per app with ``name`` and ``title`` set to ``None`` when the app has no
        migrations.

        Subclasses overriding this method should keep the same keyword-only
        parameters and preserve the row structure (including
        ``dependency_labels`` when ``plan`` is true).
        """
        if plan:
            return self._plan_migration_rows(connection, app_names)
        return self._list_migration_rows(connection, app_names)

    def _plan_migration_rows(self, connection, app_names):
        loader = MigrationLoader(connection)
        graph = loader.graph
        if app_names:
            self._validate_app_names(loader, app_names)
            targets = [key for key in graph.leaf_nodes() if key[0] in app_names]
        else:
            targets = graph.leaf_nodes()
        rows = []
        seen = set()
        for target in targets:
            for migration in graph.forwards_plan(target):
                if migration not in seen:
                    node = graph.node_map[migration]
                    name = node.key[1]
                    applied = node.key in loader.applied_migrations
                    status = (
                        MigrationStatus.APPLIED
                        if applied
                        else MigrationStatus.UNAPPLIED
                    )
                    dependency_labels = [
                        "%s.%s" % parent.key for parent in sorted(node.parents)
                    ]
                    rows.append(
                        {
                            **self._migration_row(
                                app=node.key[0],
                                name=name,
                                title=name,
                                status=status,
                                applied_at=None,
                            ),
                            "dependency_labels": dependency_labels,
                        }
                    )
                    seen.add(migration)
        return rows

    def _list_migration_rows(self, connection, app_names):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        recorder = MigrationRecorder(connection)
        recorded_migrations = recorder.applied_migrations()
        graph = loader.graph
        if app_names:
            self._validate_app_names(loader, app_names)
        else:
            app_names = sorted(loader.migrated_apps)

        rows = []
        for app_name in app_names:
            shown = set()
            for node in graph.leaf_nodes(app_name):
                for plan_node in graph.forwards_plan(node):
                    if plan_node not in shown and plan_node[0] == app_name:
                        title = plan_node[1]
                        if graph.nodes[plan_node].replaces:
                            title += " (%s squashed migrations)" % len(
                                graph.nodes[plan_node].replaces
                            )
                        applied_migration = loader.applied_migrations.get(plan_node)
                        if applied_migration:
                            if plan_node in recorded_migrations:
                                status = MigrationStatus.APPLIED
                            else:
                                status = MigrationStatus.UNRECORDED
                            applied_at = (
                                applied_migration.applied
                                if hasattr(applied_migration, "applied")
                                else None
                            )
                        else:
                            status = MigrationStatus.UNAPPLIED
                            applied_at = None
                        rows.append(
                            self._migration_row(
                                app=app_name,
                                name=plan_node[1],
                                title=title,
                                status=status,
                                applied_at=applied_at,
                            )
                        )
                        shown.add(plan_node)
            if not shown:
                rows.append(
                    self._migration_row(
                        app=app_name,
                        name=None,
                        title=None,
                        status=None,
                        applied_at=None,
                    )
                )
        return rows

    def show_list(self, migration_rows):
        """
        Print default ``showmigrations`` list output for structured list rows.

        Writes an app label before that app's migrations. Each migration line
        uses ``[X]``, ``[-]``, or ``[ ]`` for applied, unrecorded, and unapplied
        states (see :class:`.MigrationStatus`). Unrecorded rows include the
        hint to run ``migrate`` to finish recording. Placeholder rows (empty
        ``name`` and ``title``) print only the app label and ``(no migrations)``.

        When verbosity is 2 or higher, applied and unrecorded lines may append
        ``(applied at ...)`` when the row provides ``applied_at``. Expects rows
        from :meth:`get_migration_data` with ``plan=False``.
        """
        current_app = None
        for migration in migration_rows:
            app_name = migration["app"]
            if migration["name"] is None and migration["title"] is None:
                self.stdout.write(app_name, self.style.MIGRATE_LABEL)
                self.stdout.write(" (no migrations)", self.style.ERROR)
                current_app = app_name
                continue
            if app_name != current_app:
                self.stdout.write(app_name, self.style.MIGRATE_LABEL)
                current_app = app_name
            title = migration["title"]
            status = migration["status"]
            applied_at = migration["applied_at"]
            if status == MigrationStatus.APPLIED:
                output = " [X] %s" % title
                if self.verbosity >= 2 and applied_at is not None:
                    output += " (applied at %s)" % applied_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                self.stdout.write(output)
            elif status == MigrationStatus.UNRECORDED:
                display_title = title + " Run 'manage.py migrate' to finish recording."
                output = " [-] %s" % display_title
                if self.verbosity >= 2 and applied_at is not None:
                    output += " (applied at %s)" % applied_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                self.stdout.write(output)
            else:
                self.stdout.write(" [ ] %s" % title)

    def show_plan(self, migration_rows):
        """
        Print ``showmigrations --plan`` output for rows from
        :meth:`get_migration_data` with ``plan=True``.

        One line per migration: ``[X]`` or ``[ ]`` followed by ``app.name``. At
        verbosity 2 and above, append direct dependencies from each row's
        ``dependency_labels``. If ``migration_rows`` is empty, print
        ``(no migrations)``.
        """
        for entry in migration_rows:
            deps = ""
            if self.verbosity >= 2 and entry["dependency_labels"]:
                deps = " ... (%s)" % ", ".join(entry["dependency_labels"])
            if entry["status"] == MigrationStatus.APPLIED:
                self.stdout.write("[X]  %s.%s%s" % (entry["app"], entry["name"], deps))
            else:
                self.stdout.write("[ ]  %s.%s%s" % (entry["app"], entry["name"], deps))
        if not migration_rows:
            self.stdout.write("(no migrations)", self.style.ERROR)
