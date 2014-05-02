import re
import datetime

from django.db.migrations import operations
from django.db.migrations.migration import Migration
from django.db.migrations.questioner import MigrationQuestioner


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

    def changes(self, graph, trim_to_apps=None):
        """
        Main entry point to produce a list of appliable changes.
        Takes a graph to base names on and an optional set of apps
        to try and restrict to (restriction is not guaranteed)
        """
        changes = self._detect_changes()
        changes = self.arrange_for_graph(changes, graph)
        if trim_to_apps:
            changes = self._trim_to_apps(changes, trim_to_apps)
        return changes

    def _detect_changes(self):
        """
        Returns a dict of migration plans which will achieve the
        change from from_state to to_state. The dict has app labels
        as keys and a list of migrations as values.

        The resulting migrations aren't specially named, but the names
        do matter for dependencies inside the set.
        """
        # We'll store migrations as lists by app names for now
        self.migrations = {}
        old_apps = self.from_state.render()
        new_apps = self.to_state.render()
        # Prepare lists of old/new model keys that we care about
        # (i.e. ignoring proxy ones and unmigrated ones)

        old_model_keys = []
        for al, mn in self.from_state.models.keys():
            model = old_apps.get_model(al, mn)
            if not model._meta.proxy and model._meta.managed and al not in self.from_state.real_apps:
                old_model_keys.append((al, mn))

        new_model_keys = []
        for al, mn in self.to_state.models.keys():
            model = new_apps.get_model(al, mn)
            if not model._meta.proxy and model._meta.managed and al not in self.to_state.real_apps:
                new_model_keys.append((al, mn))

        def _deep_deconstruct(obj, field=True):
            """
            Recursive deconstruction for a field and its arguments.
            """
            if not hasattr(obj, 'deconstruct'):
                return obj
            deconstructed = obj.deconstruct()
            if field:
                deconstructed = deconstructed[1:]
            name, args, kwargs = deconstructed
            return (
                name,
                [_deep_deconstruct(value, field=False) for value in args],
                dict([(key, _deep_deconstruct(value, field=False))
                      for key, value in kwargs.items()])
            )

        def _rel_agnostic_fields_def(fields):
            """
            Return a definition of the fields that ignores field names and
            what related fields actually relate to.
            """
            fields_def = []
            for name, field in fields:
                deconstruction = _deep_deconstruct(field)
                if field.rel and field.rel.to:
                    del deconstruction[2]['to']
                fields_def.append(deconstruction)
            return fields_def

        # Find any renamed models.
        renamed_models = {}
        renamed_models_rel = {}
        added_models = set(new_model_keys) - set(old_model_keys)
        for app_label, model_name in added_models:
            model_state = self.to_state.models[app_label, model_name]
            model_fields_def = _rel_agnostic_fields_def(model_state.fields)

            removed_models = set(old_model_keys) - set(new_model_keys)
            for rem_app_label, rem_model_name in removed_models:
                if rem_app_label == app_label:
                    rem_model_state = self.from_state.models[rem_app_label, rem_model_name]
                    rem_model_fields_def = _rel_agnostic_fields_def(rem_model_state.fields)
                    if model_fields_def == rem_model_fields_def:
                        if self.questioner.ask_rename_model(rem_model_state, model_state):
                            self.add_to_migration(
                                app_label,
                                operations.RenameModel(
                                    old_name=rem_model_state.name,
                                    new_name=model_state.name,
                                )
                            )
                            renamed_models[app_label, model_name] = rem_model_name
                            renamed_models_rel['%s.%s' % (rem_model_state.app_label, rem_model_state.name)] = '%s.%s' % (model_state.app_label, model_state.name)
                            old_model_keys.remove((rem_app_label, rem_model_name))
                            old_model_keys.append((app_label, model_name))
                            break

        # Adding models. Phase 1 is adding models with no outward relationships.
        added_models = set(new_model_keys) - set(old_model_keys)
        pending_add = {}
        for app_label, model_name in added_models:
            model_state = self.to_state.models[app_label, model_name]
            # Are there any relationships out from this model? if so, punt it to the next phase.
            related_fields = []
            for field in new_apps.get_model(app_label, model_name)._meta.local_fields:
                if field.rel:
                    if field.rel.to:
                        related_fields.append((field.name, field.rel.to._meta.app_label, field.rel.to._meta.model_name))
                    if hasattr(field.rel, "through") and not field.rel.through._meta.auto_created:
                        related_fields.append((field.name, field.rel.through._meta.app_label, field.rel.through._meta.model_name))
            for field in new_apps.get_model(app_label, model_name)._meta.local_many_to_many:
                if field.rel.to:
                    related_fields.append((field.name, field.rel.to._meta.app_label, field.rel.to._meta.model_name))
                if hasattr(field.rel, "through") and not field.rel.through._meta.auto_created:
                    related_fields.append((field.name, field.rel.through._meta.app_label, field.rel.through._meta.model_name))
            if related_fields:
                pending_add[app_label, model_name] = related_fields
            else:
                self.add_to_migration(
                    app_label,
                    operations.CreateModel(
                        name=model_state.name,
                        fields=model_state.fields,
                        options=model_state.options,
                        bases=model_state.bases,
                    )
                )

        # Phase 2 is progressively adding pending models, splitting up into two
        # migrations if required.
        pending_new_fks = []
        pending_unique_together = []
        added_phase_2 = set()
        while pending_add:
            # Is there one we can add that has all dependencies satisfied?
            satisfied = [
                (m, rf)
                for m, rf in pending_add.items()
                if all((al, mn) not in pending_add for f, al, mn in rf)
            ]
            if satisfied:
                (app_label, model_name), related_fields = sorted(satisfied)[0]
                model_state = self.to_state.models[app_label, model_name]
                self.add_to_migration(
                    app_label,
                    operations.CreateModel(
                        name=model_state.name,
                        fields=model_state.fields,
                        options=model_state.options,
                        bases=model_state.bases,
                    ),
                    # If it's already been added in phase 2 put it in a new
                    # migration for safety.
                    new=any((al, mn) in added_phase_2 for f, al, mn in related_fields),
                )
                added_phase_2.add((app_label, model_name))
            # Ah well, we'll need to split one. Pick deterministically.
            else:
                (app_label, model_name), related_fields = sorted(pending_add.items())[0]
                model_state = self.to_state.models[app_label, model_name]
                # Defer unique together constraints creation, see ticket #22275
                unique_together_constraints = model_state.options.pop('unique_together', None)
                if unique_together_constraints:
                    pending_unique_together.append((app_label, model_name,
                                                   unique_together_constraints))
                # Work out the fields that need splitting out
                bad_fields = dict((f, (al, mn)) for f, al, mn in related_fields if (al, mn) in pending_add)
                # Create the model, without those
                self.add_to_migration(
                    app_label,
                    operations.CreateModel(
                        name=model_state.name,
                        fields=[(n, f) for n, f in model_state.fields if n not in bad_fields],
                        options=model_state.options,
                        bases=model_state.bases,
                    )
                )
                # Add the bad fields to be made in a phase 3
                for field_name, (other_app_label, other_model_name) in bad_fields.items():
                    pending_new_fks.append((app_label, model_name, field_name, other_app_label))
            for field_name, other_app_label, other_model_name in related_fields:
                # If it depends on a swappable something, add a dynamic depend'cy
                swappable_setting = new_apps.get_model(app_label, model_name)._meta.get_field_by_name(field_name)[0].swappable_setting
                if swappable_setting is not None:
                    self.add_swappable_dependency(app_label, swappable_setting)
                elif app_label != other_app_label:
                    self.add_dependency(app_label, other_app_label)
            del pending_add[app_label, model_name]

        # Phase 3 is adding the final set of FKs as separate new migrations.
        for app_label, model_name, field_name, other_app_label in pending_new_fks:
            model_state = self.to_state.models[app_label, model_name]
            self.add_to_migration(
                app_label,
                operations.AddField(
                    model_name=model_name,
                    name=field_name,
                    field=model_state.get_field_by_name(field_name),
                ),
                new=True,
            )
            # If it depends on a swappable something, add a dynamic depend'cy
            swappable_setting = new_apps.get_model(app_label, model_name)._meta.get_field_by_name(field_name)[0].swappable_setting
            if swappable_setting is not None:
                self.add_swappable_dependency(app_label, swappable_setting)
            elif app_label != other_app_label:
                self.add_dependency(app_label, other_app_label)
        # Phase 3.1 - unique together constraints
        for app_label, model_name, unique_together in pending_unique_together:
            self.add_to_migration(
                app_label,
                operations.AlterUniqueTogether(
                    name=model_name,
                    unique_together=unique_together
                )
            )
        # Changes within models
        kept_models = set(old_model_keys).intersection(new_model_keys)
        old_fields = set()
        new_fields = set()
        unique_together_operations = []
        for app_label, model_name in kept_models:
            old_model_name = renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            # Collect field changes for later global dealing with (so AddFields
            # always come before AlterFields even on separate models)
            old_fields.update((app_label, model_name, x) for x, y in old_model_state.fields)
            new_fields.update((app_label, model_name, x) for x, y in new_model_state.fields)
            # Unique_together changes. Operations will be added to migration a
            # bit later, after fields creation. See ticket #22035.
            if old_model_state.options.get("unique_together", set()) != new_model_state.options.get("unique_together", set()):
                unique_together_operations.append((
                    app_label,
                    operations.AlterUniqueTogether(
                        name=model_name,
                        unique_together=new_model_state.options.get("unique_together", set()),
                    )
                ))
        # New fields
        renamed_fields = {}
        for app_label, model_name, field_name in new_fields - old_fields:
            old_model_name = renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            field = new_model_state.get_field_by_name(field_name)
            # Scan to see if this is actually a rename!
            field_dec = _deep_deconstruct(field)
            found_rename = False
            for rem_app_label, rem_model_name, rem_field_name in (old_fields - new_fields):
                if rem_app_label == app_label and rem_model_name == model_name:
                    old_field_dec = _deep_deconstruct(old_model_state.get_field_by_name(rem_field_name))
                    if field.rel and field.rel.to and 'to' in old_field_dec[2]:
                        old_rel_to = old_field_dec[2]['to']
                        if old_rel_to in renamed_models_rel:
                            old_field_dec[2]['to'] = renamed_models_rel[old_rel_to]
                    if old_field_dec == field_dec:
                        if self.questioner.ask_rename(model_name, rem_field_name, field_name, field):
                            self.add_to_migration(
                                app_label,
                                operations.RenameField(
                                    model_name=model_name,
                                    old_name=rem_field_name,
                                    new_name=field_name,
                                )
                            )
                            old_fields.remove((rem_app_label, rem_model_name, rem_field_name))
                            old_fields.add((app_label, model_name, field_name))
                            renamed_fields[app_label, model_name, field_name] = rem_field_name
                            found_rename = True
                            break
            if found_rename:
                continue
            # You can't just add NOT NULL fields with no default
            if not field.null and not field.has_default():
                field = field.clone()
                field.default = self.questioner.ask_not_null_addition(field_name, model_name)
                self.add_to_migration(
                    app_label,
                    operations.AddField(
                        model_name=model_name,
                        name=field_name,
                        field=field,
                        preserve_default=False,
                    )
                )
            else:
                self.add_to_migration(
                    app_label,
                    operations.AddField(
                        model_name=model_name,
                        name=field_name,
                        field=field,
                    )
                )
                new_field = new_apps.get_model(app_label, model_name)._meta.get_field_by_name(field_name)[0]
                swappable_setting = getattr(new_field, 'swappable_setting', None)
                if swappable_setting is not None:
                    self.add_swappable_dependency(app_label, swappable_setting)
        # Old fields
        for app_label, model_name, field_name in old_fields - new_fields:
            old_model_name = renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            self.add_to_migration(
                app_label,
                operations.RemoveField(
                    model_name=model_name,
                    name=field_name,
                )
            )
        # The same fields
        for app_label, model_name, field_name in old_fields.intersection(new_fields):
            # Did the field change?
            old_model_name = renamed_models.get((app_label, model_name), model_name)
            old_model_state = self.from_state.models[app_label, old_model_name]
            new_model_state = self.to_state.models[app_label, model_name]
            old_field_name = renamed_fields.get((app_label, model_name, field_name), field_name)
            old_field_dec = _deep_deconstruct(old_model_state.get_field_by_name(old_field_name))
            new_field_dec = _deep_deconstruct(new_model_state.get_field_by_name(field_name))
            if old_field_dec != new_field_dec:
                self.add_to_migration(
                    app_label,
                    operations.AlterField(
                        model_name=model_name,
                        name=field_name,
                        field=new_model_state.get_field_by_name(field_name),
                    )
                )
        for app_label, operation in unique_together_operations:
            self.add_to_migration(app_label, operation)
        # Removing models
        removed_models = set(old_model_keys) - set(new_model_keys)
        for app_label, model_name in removed_models:
            model_state = self.from_state.models[app_label, model_name]
            self.add_to_migration(
                app_label,
                operations.DeleteModel(
                    model_state.name,
                )
            )
        # Alright, now add internal dependencies
        for app_label, migrations in self.migrations.items():
            for m1, m2 in zip(migrations, migrations[1:]):
                m2.dependencies.append((app_label, m1.name))
        # Clean up dependencies
        for app_label, migrations in self.migrations.items():
            for migration in migrations:
                migration.dependencies = list(set(migration.dependencies))
        return self.migrations

    def add_to_migration(self, app_label, operation, new=False):
        migrations = self.migrations.setdefault(app_label, [])
        if not migrations or new:
            subclass = type("Migration", (Migration,), {"operations": [], "dependencies": []})
            instance = subclass("auto_%i" % (len(migrations) + 1), app_label)
            migrations.append(instance)
        migrations[-1].operations.append(operation)

    def add_dependency(self, app_label, other_app_label):
        """
        Adds a dependency to app_label's newest migration on
        other_app_label's latest migration.
        """
        if self.migrations.get(other_app_label):
            dependency = (other_app_label, self.migrations[other_app_label][-1].name)
        else:
            dependency = (other_app_label, "__first__")
        self.migrations[app_label][-1].dependencies.append(dependency)

    def add_swappable_dependency(self, app_label, setting_name):
        """
        Adds a dependency to the value of a swappable model setting.
        """
        dependency = ("__setting__", setting_name)
        self.migrations[app_label][-1].dependencies.append(dependency)

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
                continue
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
                    new_name = "%04i_%s" % (
                        next_number,
                        self.suggest_name(migration.operations)[:100],
                    )
                name_map[(app_label, migration.name)] = (app_label, new_name)
                next_number += 1
                migration.name = new_name
        # Now fix dependencies
        for app_label, migrations in changes.items():
            for migration in migrations:
                migration.dependencies = [name_map.get(d, d) for d in migration.dependencies]
        return changes

    def _trim_to_apps(self, changes, app_labels):
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
        they might represent. Names are not guaranteed to be unique,
        but we put some effort in to the fallback name to avoid VCS conflicts
        if we can.
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
        elif len(ops) > 1:
            if all(isinstance(o, operations.CreateModel) for o in ops):
                return "_".join(sorted(o.name.lower() for o in ops))
        return "auto_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M")

    @classmethod
    def parse_number(cls, name):
        """
        Given a migration name, tries to extract a number from the
        beginning of it. If no number found, returns None.
        """
        if re.match(r"^\d+_", name):
            return int(name.split("_")[0])
        return None
