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
    depends on first). A user interface may offer single-app detection
    if it wishes, with the caveat that it may not always be possible.
    """

    def __init__(self, from_state, to_state):
        self.from_state = from_state
        self.to_state = to_state

    def changes(self):
        """
        Returns a set of migration plans which will achieve the
        change from from_state to to_state.
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
        # Flatten and return
        result = set()
        for app_label, migrations in self.migrations.items():
            for migration in migrations:
                subclass = type("Migration", (Migration,), migration)
                instance = subclass(migration['name'], app_label)
                result.add(instance)
        return result

    def add_to_migration(self, app_label, operation):
        migrations = self.migrations.setdefault(app_label, [])
        if not migrations:
            migrations.append({"name": "auto_%i" % (len(migrations) + 1), "operations": [], "dependencies": []})
        migrations[-1]['operations'].append(operation)
