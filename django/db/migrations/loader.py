from __future__ import unicode_literals

import os
import sys
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.db.migrations.graph import MigrationGraph, NodeNotFoundError
from django.db.migrations.recorder import MigrationRecorder
from django.utils import six

MIGRATIONS_MODULE_NAME = 'migrations'


class MigrationLoader(object):
    """
    Loads migration files from disk, and their status from the database.

    Migration files are expected to live in the "migrations" directory of
    an app. Their names are entirely unimportant from a code perspective,
    but will probably follow the 1234_name.py convention.

    On initialization, this class will scan those directories, and open and
    read the python files, looking for a class called Migration, which should
    inherit from django.db.migrations.Migration. See
    django.db.migrations.migration for what that looks like.

    Some migrations will be marked as "replacing" another set of migrations.
    These are loaded into a separate set of migrations away from the main ones.
    If all the migrations they replace are either unapplied or missing from
    disk, then they are injected into the main set, replacing the named migrations.
    Any dependency pointers to the replaced migrations are re-pointed to the
    new migration.

    This does mean that this class MUST also talk to the database as well as
    to disk, but this is probably fine. We're already not just operating
    in memory.
    """

    def __init__(self, connection, load=True, ignore_no_migrations=False):
        self.connection = connection
        self.disk_migrations = None
        self.applied_migrations = None
        self.ignore_no_migrations = ignore_no_migrations
        if load:
            self.build_graph()

    @classmethod
    def migrations_module(cls, app_label):
        if app_label in settings.MIGRATION_MODULES:
            return settings.MIGRATION_MODULES[app_label]
        else:
            app_package_name = apps.get_app_config(app_label).name
            return '%s.%s' % (app_package_name, MIGRATIONS_MODULE_NAME)

    def load_disk(self):
        """
        Loads the migrations from all INSTALLED_APPS from disk.
        """
        self.disk_migrations = {}
        self.unmigrated_apps = set()
        self.migrated_apps = set()
        for app_config in apps.get_app_configs():
            # Get the migrations module directory
            module_name = self.migrations_module(app_config.label)
            was_loaded = module_name in sys.modules
            try:
                module = import_module(module_name)
            except ImportError as e:
                # I hate doing this, but I don't want to squash other import errors.
                # Might be better to try a directory check directly.
                if "No module named" in str(e) and MIGRATIONS_MODULE_NAME in str(e):
                    self.unmigrated_apps.add(app_config.label)
                    continue
                raise
            else:
                # PY3 will happily import empty dirs as namespaces.
                if not hasattr(module, '__file__'):
                    self.unmigrated_apps.add(app_config.label)
                    continue
                # Module is not a package (e.g. migrations.py).
                if not hasattr(module, '__path__'):
                    self.unmigrated_apps.add(app_config.label)
                    continue
                # Force a reload if it's already loaded (tests need this)
                if was_loaded:
                    six.moves.reload_module(module)
            self.migrated_apps.add(app_config.label)
            directory = os.path.dirname(module.__file__)
            # Scan for .py files
            migration_names = set()
            for name in os.listdir(directory):
                if name.endswith(".py"):
                    import_name = name.rsplit(".", 1)[0]
                    if import_name[0] not in "_.~":
                        migration_names.add(import_name)
            # Load them
            south_style_migrations = False
            django_style_migrations = False
            for migration_name in migration_names:
                try:
                    migration_module = import_module("%s.%s" % (module_name, migration_name))
                except ImportError as e:
                    # Ignore South import errors, as we're triggering them
                    if "south" in str(e).lower():
                        south_style_migrations = True
                        break
                    raise
                if not hasattr(migration_module, "Migration"):
                    raise BadMigrationError(
                        "Migration %s in app %s has no Migration class" % (migration_name, app_config.label)
                    )
                # Ignore South-style migrations
                if hasattr(migration_module.Migration, "forwards"):
                    south_style_migrations = True
                    break
                self.disk_migrations[app_config.label, migration_name] = migration_module.Migration(migration_name, app_config.label)
                django_style_migrations = True

            if south_style_migrations:
                if django_style_migrations:
                    raise BadMigrationError(
                        "Migrated app %r contains South migrations. Make sure "
                        "all numbered South migrations are deleted prior to "
                        "creating Django migrations." % app_config.label
                    )
                self.unmigrated_apps.add(app_config.label)

    def get_migration(self, app_label, name_prefix):
        "Gets the migration exactly named, or raises `graph.NodeNotFoundError`"
        return self.graph.nodes[app_label, name_prefix]

    def get_migration_by_prefix(self, app_label, name_prefix):
        "Returns the migration(s) which match the given app label and name _prefix_"
        # Do the search
        results = []
        for l, n in self.disk_migrations:
            if l == app_label and n.startswith(name_prefix):
                results.append((l, n))
        if len(results) > 1:
            raise AmbiguityError(
                "There is more than one migration for '%s' with the prefix '%s'" % (app_label, name_prefix)
            )
        elif len(results) == 0:
            raise KeyError("There no migrations for '%s' with the prefix '%s'" % (app_label, name_prefix))
        else:
            return self.disk_migrations[results[0]]

    def check_key(self, key, current_app):
        if (key[1] != "__first__" and key[1] != "__latest__") or key in self.graph:
            return key
        # Special-case __first__, which means "the first migration" for
        # migrated apps, and is ignored for unmigrated apps. It allows
        # makemigrations to declare dependencies on apps before they even have
        # migrations.
        if key[0] == current_app:
            # Ignore __first__ references to the same app (#22325)
            return
        if key[0] in self.unmigrated_apps:
            # This app isn't migrated, but something depends on it.
            # The models will get auto-added into the state, though
            # so we're fine.
            return
        if key[0] in self.migrated_apps:
            try:
                if key[1] == "__first__":
                    return list(self.graph.root_nodes(key[0]))[0]
                else:  # "__latest__"
                    return list(self.graph.leaf_nodes(key[0]))[0]
            except IndexError:
                if self.ignore_no_migrations:
                    return None
                else:
                    raise ValueError("Dependency on app with no migrations: %s" % key[0])
        raise ValueError("Dependency on unknown app: %s" % key[0])

    def build_graph(self):
        """
        Builds a migration dependency graph using both the disk and database.
        You'll need to rebuild the graph if you apply migrations. This isn't
        usually a problem as generally migration stuff runs in a one-shot process.
        """
        # Load disk data
        self.load_disk()
        # Load database data
        if self.connection is None:
            self.applied_migrations = set()
        else:
            recorder = MigrationRecorder(self.connection)
            self.applied_migrations = recorder.applied_migrations()
        # Do a first pass to separate out replacing and non-replacing migrations
        normal = {}
        replacing = {}
        for key, migration in self.disk_migrations.items():
            if migration.replaces:
                replacing[key] = migration
            else:
                normal[key] = migration
        # Calculate reverse dependencies - i.e., for each migration, what depends on it?
        # This is just for dependency re-pointing when applying replacements,
        # so we ignore run_before here.
        reverse_dependencies = {}
        for key, migration in normal.items():
            for parent in migration.dependencies:
                reverse_dependencies.setdefault(parent, set()).add(key)
        # Remember the possible replacements to generate more meaningful error
        # messages
        reverse_replacements = {}
        for key, migration in replacing.items():
            for replaced in migration.replaces:
                reverse_replacements.setdefault(replaced, set()).add(key)
        # Carry out replacements if we can - that is, if all replaced migrations
        # are either unapplied or missing.
        for key, migration in replacing.items():
            # Ensure this replacement migration is not in applied_migrations
            self.applied_migrations.discard(key)
            # Do the check. We can replace if all our replace targets are
            # applied, or if all of them are unapplied.
            applied_statuses = [(target in self.applied_migrations) for target in migration.replaces]
            can_replace = all(applied_statuses) or (not any(applied_statuses))
            if not can_replace:
                continue
            # Alright, time to replace. Step through the replaced migrations
            # and remove, repointing dependencies if needs be.
            for replaced in migration.replaces:
                if replaced in normal:
                    # We don't care if the replaced migration doesn't exist;
                    # the usage pattern here is to delete things after a while.
                    del normal[replaced]
                for child_key in reverse_dependencies.get(replaced, set()):
                    if child_key in migration.replaces:
                        continue
                    # List of migrations whose dependency on `replaced` needs
                    # to be updated to a dependency on `key`.
                    to_update = []
                    # Child key may itself be replaced, in which case it might
                    # not be in `normal` anymore (depending on whether we've
                    # processed its replacement yet). If it's present, we go
                    # ahead and update it; it may be deleted later on if it is
                    # replaced, but there's no harm in updating it regardless.
                    if child_key in normal:
                        to_update.append(normal[child_key])
                    # If the child key is replaced, we update its replacement's
                    # dependencies too, if necessary. (We don't know if this
                    # replacement will actually take effect or not, but either
                    # way it's OK to update the replacing migration).
                    if child_key in reverse_replacements:
                        for replaces_child_key in reverse_replacements[child_key]:
                            if replaced in replacing[replaces_child_key].dependencies:
                                to_update.append(replacing[replaces_child_key])
                    # Actually perform the dependency update on all migrations
                    # that require it.
                    for migration_needing_update in to_update:
                        migration_needing_update.dependencies.remove(replaced)
                        migration_needing_update.dependencies.append(key)
            normal[key] = migration
            # Mark the replacement as applied if all its replaced ones are
            if all(applied_statuses):
                self.applied_migrations.add(key)
        # Store the replacement migrations for later checks
        self.replacements = replacing
        # Finally, make a graph and load everything into it
        self.graph = MigrationGraph()
        for key, migration in normal.items():
            self.graph.add_node(key, migration)

        def _reraise_missing_dependency(migration, missing, exc):
            """
            Checks if ``missing`` could have been replaced by any squash
            migration but wasn't because the the squash migration was partially
            applied before. In that case raise a more understandable exception.

            #23556
            """
            if missing in reverse_replacements:
                candidates = reverse_replacements.get(missing, set())
                is_replaced = any(candidate in self.graph.nodes for candidate in candidates)
                if not is_replaced:
                    tries = ', '.join('%s.%s' % c for c in candidates)
                    exc_value = NodeNotFoundError(
                        "Migration {0} depends on nonexistent node ('{1}', '{2}'). "
                        "Django tried to replace migration {1}.{2} with any of [{3}] "
                        "but wasn't able to because some of the replaced migrations "
                        "are already applied.".format(
                            migration, missing[0], missing[1], tries
                        ),
                        missing)
                    exc_value.__cause__ = exc
                    six.reraise(NodeNotFoundError, exc_value, sys.exc_info()[2])
            raise exc

        # Add all internal dependencies first to ensure __first__ dependencies
        # find the correct root node.
        for key, migration in normal.items():
            for parent in migration.dependencies:
                if parent[0] != key[0] or parent[1] == '__first__':
                    # Ignore __first__ references to the same app (#22325)
                    continue
                try:
                    self.graph.add_dependency(migration, key, parent)
                except NodeNotFoundError as e:
                    # Since we added "key" to the nodes before this implies
                    # "parent" is not in there. To make the raised exception
                    # more understandable we check if parent could have been
                    # replaced but hasn't (eg partially applied squashed
                    # migration)
                    _reraise_missing_dependency(migration, parent, e)
        for key, migration in normal.items():
            for parent in migration.dependencies:
                if parent[0] == key[0]:
                    # Internal dependencies already added.
                    continue
                parent = self.check_key(parent, key[0])
                if parent is not None:
                    try:
                        self.graph.add_dependency(migration, key, parent)
                    except NodeNotFoundError as e:
                        # Since we added "key" to the nodes before this implies
                        # "parent" is not in there.
                        _reraise_missing_dependency(migration, parent, e)
            for child in migration.run_before:
                child = self.check_key(child, key[0])
                if child is not None:
                    try:
                        self.graph.add_dependency(migration, child, key)
                    except NodeNotFoundError as e:
                        # Since we added "key" to the nodes before this implies
                        # "child" is not in there.
                        _reraise_missing_dependency(migration, child, e)

    def detect_conflicts(self):
        """
        Looks through the loaded graph and detects any conflicts - apps
        with more than one leaf migration. Returns a dict of the app labels
        that conflict with the migration names that conflict.
        """
        seen_apps = {}
        conflicting_apps = set()
        for app_label, migration_name in self.graph.leaf_nodes():
            if app_label in seen_apps:
                conflicting_apps.add(app_label)
            seen_apps.setdefault(app_label, set()).add(migration_name)
        return {app_label: seen_apps[app_label] for app_label in conflicting_apps}

    def project_state(self, nodes=None, at_end=True):
        """
        Returns a ProjectState object representing the most recent state
        that the migrations we loaded represent.

        See graph.make_state for the meaning of "nodes" and "at_end"
        """
        return self.graph.make_state(nodes=nodes, at_end=at_end, real_apps=list(self.unmigrated_apps))


class BadMigrationError(Exception):
    """
    Raised when there's a bad migration (unreadable/bad format/etc.)
    """
    pass


class AmbiguityError(Exception):
    """
    Raised when more than one migration matches a name prefix
    """
    pass
