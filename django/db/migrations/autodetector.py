import re
import sys
from django.utils import datetime_safe
from django.utils.six.moves import input
from django.db.migrations import operations
from django.db.migrations.migration import Migration
from django.db.models.loading import cache


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

    def __init__(self, from_state, to_state, questioner=None):
        self.from_state = from_state
        self.to_state = to_state
        self.questioner = questioner or MigrationQuestioner()

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
        # Adding models.
        added_models = set(self.to_state.models.keys()) - set(self.from_state.models.keys())
        for app_label, model_name in added_models:
            model_state = self.to_state.models[app_label, model_name]
            self.add_to_migration(
                app_label,
                operations.CreateModel(
                    name = model_state.name,
                    fields = model_state.fields,
                    options = model_state.options,
                    bases = model_state.bases,
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
        # Changes within models
        kept_models = set(self.from_state.models.keys()).intersection(self.to_state.models.keys())
        for app_label, model_name in kept_models:
            old_model_state = self.from_state.models[app_label, model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            # New fields
            old_field_names = set([x for x, y in old_model_state.fields])
            new_field_names = set([x for x, y in new_model_state.fields])
            for field_name in new_field_names - old_field_names:
                field = new_model_state.get_field_by_name(field_name)
                # Scan to see if this is actually a rename!
                field_dec = field.deconstruct()[1:]
                found_rename = False
                for removed_field_name in (old_field_names - new_field_names):
                    if old_model_state.get_field_by_name(removed_field_name).deconstruct()[1:] == field_dec:
                        self.add_to_migration(
                            app_label,
                            operations.RenameField(
                                model_name = model_name,
                                old_name = removed_field_name,
                                new_name = field_name,
                            )
                        )
                        old_field_names.remove(removed_field_name)
                        new_field_names.remove(field_name)
                        found_rename = True
                        break
                if found_rename:
                    continue
                # You can't just add NOT NULL fields with no default
                if not field.null and not field.has_default():
                    field.default = self.questioner.ask_not_null_addition(field_name, model_name)
                self.add_to_migration(
                    app_label,
                    operations.AddField(
                        model_name = model_name,
                        name = field_name,
                        field = field,
                    )
                )
            # Old fields
            for field_name in old_field_names - new_field_names:
                self.add_to_migration(
                    app_label,
                    operations.RemoveField(
                        model_name = model_name,
                        name = field_name,
                    )
                )
            # The same fields
            for field_name in old_field_names.intersection(new_field_names):
                # Did the field change?
                old_field_dec = old_model_state.get_field_by_name(field_name).deconstruct()
                new_field_dec = new_model_state.get_field_by_name(field_name).deconstruct()
                if old_field_dec != new_field_dec:
                    self.add_to_migration(
                        app_label,
                        operations.AlterField(
                            model_name = model_name,
                            name = field_name,
                            field = new_model_state.get_field_by_name(field_name),
                        )
                    )
        # Alright, now add internal dependencies
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

    def arrange_for_graph(self, changes, graph):
        """
        Takes in a result from changes() and a MigrationGraph,
        and fixes the names and dependencies of the changes so they
        extend the graph from the leaf nodes for each app.
        """
        leaves = graph.leaf_nodes()
        name_map = {}
        for app_label, migrations in list(changes.items()):
            if not migrations:
                continue
            # Find the app label's current leaf node
            app_leaf = None
            for leaf in leaves:
                if leaf[0] == app_label:
                    app_leaf = leaf
                    break
            # Do they want an initial migration for this app?
            if app_leaf is None and not self.questioner.ask_initial(app_label):
                # They don't.
                for migration in migrations:
                    name_map[(app_label, migration.name)] = (app_label, "__first__")
                del changes[app_label]
            # Work out the next number in the sequence
            if app_leaf is None:
                next_number = 1
            else:
                next_number = (self.parse_number(app_leaf[1]) or 0) + 1
            # Name each migration
            for i, migration in enumerate(migrations):
                if i == 0 and app_leaf:
                    migration.dependencies.append(app_leaf)
                if i == 0 and not app_leaf:
                    new_name = "0001_initial"
                else:
                    new_name = "%04i_%s" % (next_number, self.suggest_name(migration.operations))
                name_map[(app_label, migration.name)] = (app_label, new_name)
                migration.name = new_name
        # Now fix dependencies
        for app_label, migrations in changes.items():
            for migration in migrations:
                migration.dependencies = [name_map.get(d, d) for d in migration.dependencies]
        return changes

    def trim_to_apps(self, changes, app_labels):
        """
        Takes changes from arrange_for_graph and set of app labels and
        returns a modified set of changes which trims out as many migrations
        that are not in app_labels as possible.
        Note that some other migrations may still be present, as they may be
        required dependencies.
        """
        # Gather other app dependencies in a first pass
        app_dependencies = {}
        for app_label, migrations in changes.items():
            for migration in migrations:
                for dep_app_label, name in migration.dependencies:
                    app_dependencies.setdefault(app_label, set()).add(dep_app_label)
        required_apps = set(app_labels)
        # Keep resolving till there's no change
        old_required_apps = None
        while old_required_apps != required_apps:
            old_required_apps = set(required_apps)
            for app_label in list(required_apps):
                required_apps.update(app_dependencies.get(app_label, set()))
        # Remove all migrations that aren't needed
        for app_label in list(changes.keys()):
            if app_label not in required_apps:
                del changes[app_label]
        return changes

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
            elif isinstance(ops[0], operations.AddField):
                return "%s_%s" % (ops[0].model_name.lower(), ops[0].name.lower())
            elif isinstance(ops[0], operations.RemoveField):
                return "remove_%s_%s" % (ops[0].model_name.lower(), ops[0].name.lower())
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


class MigrationQuestioner(object):
    """
    Gives the autodetector responses to questions it might have.
    This base class has a built-in noninteractive mode, but the
    interactive subclass is what the command-line arguments will use.
    """

    def __init__(self, defaults=None):
        self.defaults = defaults or {}

    def ask_initial(self, app_label):
        "Should we create an initial migration for the app?"
        return self.defaults.get("ask_initial", False)

    def ask_not_null_addition(self, field_name, model_name):
        "Adding a NOT NULL field to a model"
        # None means quit
        return None


class InteractiveMigrationQuestioner(MigrationQuestioner):

    def __init__(self, specified_apps=set()):
        self.specified_apps = specified_apps

    def _boolean_input(self, question):
        result = input("%s " % question)
        while len(result) < 1 or result[0].lower() not in "yn":
            result = input("Please answer yes or no: ")
        return result[0].lower() == "y"

    def _choice_input(self, question, choices):
        print question
        for i, choice in enumerate(choices):
            print " %s) %s" % (i + 1, choice)
        result = input("Select an option: ")
        while True:
            try:
                value = int(result)
                if 0 < value <= len(choices):
                    return value
            except ValueError:
                pass
            result = input("Please select a valid option: ")

    def ask_initial(self, app_label):
        "Should we create an initial migration for the app?"
        # Don't ask for django.contrib apps
        app = cache.get_app(app_label)
        if app.__name__.startswith("django.contrib"):
            return False
        # If it was specified on the command line, definitely true
        if app_label in self.specified_apps:
            return True
        # Now ask
        return self._boolean_input("Do you want to enable migrations for app '%s'?" % app_label)

    def ask_not_null_addition(self, field_name, model_name):
        "Adding a NOT NULL field to a model"
        choice = self._choice_input(
            "You are trying to add a non-nullable field '%s' to %s without a default;\n" % (field_name, model_name) +
            "this is not possible. Please select a fix:",
            [
                "Provide a one-off default now (will be set on all existing rows)",
                "Quit, and let me add a default in models.py",
            ]
        )
        if choice == 2:
            sys.exit(3)
        else:
            print("Please enter the default value now, as valid Python")
            print("The datetime module is available, so you can do e.g. datetime.date.today()")
            while True:
                code = input(">>> ")
                if not code:
                    print("Please enter some code, or 'exit' (with no quotes) to exit.")
                elif code == "exit":
                    sys.exit(1)
                else:
                    try:
                        return eval(code, {}, {"datetime": datetime_safe})
                    except (SyntaxError, NameError) as e:
                        print("Invalid input: %s" % e)
                    else:
                        break
