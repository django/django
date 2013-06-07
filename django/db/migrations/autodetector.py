import re
from django.db.migrations import operations
from django.db.migrations.migration import Migration


class MigrationAutodetector(object):
    """
    Takes a pair of ProjectStates, and compares them to see what the
    first would need doing to make it match the second (the second
    usually being the project's current state).

    Note that this naturally operates on entire projects at a time,
    as it's likely that changes interact (for example, you can't
    add a ForeignKey without having a migration to add the table it
    depends on first). A user interface may offer single-app usage
    if it wishes, with the caveat that it may not always be possible.
    """

    def __init__(self, from_state, to_state):
        self.from_state = from_state
        self.to_state = to_state

    def changes(self):
        """
        Returns a dict of migration plans which will achieve the
        change from from_state to to_state. The dict has app labels
        as kays and a list of migrations as values.

        The resulting migrations aren't specially named, but the names
        do matter for dependencies inside the set.
        """
        # We'll store migrations as lists by app names for now
        self.migrations = {}
        # Stage one: Adding models.
        added_models = set(self.to_state.models.keys()) - set(self.from_state.models.keys())
        for app_label, model_name in added_models:
            model_state = self.to_state.models[app_label, model_name]
            self.add_to_migration(
                app_label,
                operations.CreateModel(
                    model_state.name,
                    model_state.fields,
                    model_state.options,
                    model_state.bases,
                )
            )
        # Removing models
        removed_models = set(self.from_state.models.keys()) - set(self.to_state.models.keys())
        for app_label, model_name in removed_models:
            model_state = self.from_state.models[app_label, model_name]
            self.add_to_migration(
                app_label,
                operations.DeleteModel(
                    model_state.name,
                )
            )
        # Alright, now sort out and return the migrations
        for app_label, migrations in self.migrations.items():
            for m1, m2 in zip(migrations, migrations[1:]):
                m2.dependencies.append((app_label, m1.name))
        return self.migrations

    def add_to_migration(self, app_label, operation):
        migrations = self.migrations.setdefault(app_label, [])
        if not migrations:
            subclass = type("Migration", (Migration,), {"operations": [], "dependencies": []})
            instance = subclass("auto_%i" % (len(migrations) + 1), app_label)
            migrations.append(instance)
        migrations[-1].operations.append(operation)

    @classmethod
    def suggest_name(cls, ops):
        """
        Given a set of operations, suggests a name for the migration
        they might represent. Names not guaranteed to be unique; they
        must be prefixed by a number or date.
        """
        if len(ops) == 1:
            if isinstance(ops[0], operations.CreateModel):
                return ops[0].name.lower()
            elif isinstance(ops[0], operations.DeleteModel):
                return "delete_%s" % ops[0].name.lower()
        elif all(isinstance(o, operations.CreateModel) for o in ops):
            return "_".join(sorted(o.name.lower() for o in ops))
        return "auto"

    @classmethod
    def parse_number(cls, name):
        """
        Given a migration name, tries to extract a number from the
        beginning of it. If no number found, returns None.
        """
        if re.match(r"^\d+_", name):
            return int(name.split("_")[0])
        return None

    @classmethod
    def arrange_for_graph(cls, changes, graph):
        """
        Takes in a result from changes() and a MigrationGraph,
        and fixes the names and dependencies of the changes so they
        extend the graph from the leaf nodes for each app.
        """
        leaves = graph.leaf_nodes()
        name_map = {}
        for app_label, migrations in changes.items():
            if not migrations:
                continue
            # Find the app label's current leaf node
            app_leaf = None
            for leaf in leaves:
                if leaf[0] == app_label:
                    app_leaf = leaf
                    break
            # Work out the next number in the sequence
            if app_leaf is None:
                next_number = 1
            else:
                next_number = (cls.parse_number(app_leaf[1]) or 0) + 1
            # Name each migration
            for i, migration in enumerate(migrations):
                if i == 0 and app_leaf:
                    migration.dependencies.append(app_leaf)
                if i == 0 and not app_leaf:
                    new_name = "0001_initial"
                else:
                    new_name = "%04i_%s" % (next_number, cls.suggest_name(migration.operations))
                name_map[(app_label, migration.name)] = (app_label, new_name)
                migration.name = new_name
        # Now fix dependencies
        for app_label, migrations in changes.items():
            for migration in migrations:
                migration.dependencies = [name_map.get(d, d) for d in migration.dependencies]
        return changes
