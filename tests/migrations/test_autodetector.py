# encoding: utf8
from django.test import TestCase
from django.db.migrations.autodetector import MigrationAutodetector, MigrationQuestioner
from django.db.migrations.state import ProjectState, ModelState
from django.db.migrations.graph import MigrationGraph
from django.db import models


class AutodetectorTests(TestCase):
    """
    Tests the migration autodetector.
    """

    author_empty = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True))])
    author_name = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200))])
    author_name_longer = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=400))])
    author_name_renamed = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("names", models.CharField(max_length=200))])
    other_pony = ModelState("otherapp", "Pony", [("id", models.AutoField(primary_key=True))])
    other_stable = ModelState("otherapp", "Stable", [("id", models.AutoField(primary_key=True))])
    third_thing = ModelState("thirdapp", "Thing", [("id", models.AutoField(primary_key=True))])

    def make_project_state(self, model_states):
        "Shortcut to make ProjectStates from lists of predefined models"
        project_state = ProjectState()
        for model_state in model_states:
            project_state.add_model_state(model_state.clone())
        return project_state

    def test_arrange_for_graph(self):
        "Tests auto-naming of migrations for graph matching."
        # Make a fake graph
        graph = MigrationGraph()
        graph.add_node(("testapp", "0001_initial"), None)
        graph.add_node(("testapp", "0002_foobar"), None)
        graph.add_node(("otherapp", "0001_initial"), None)
        graph.add_dependency(("testapp", "0002_foobar"), ("testapp", "0001_initial"))
        graph.add_dependency(("testapp", "0002_foobar"), ("otherapp", "0001_initial"))
        # Use project state to make a new migration change set
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty, self.other_pony, self.other_stable])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector.changes()
        # Run through arrange_for_graph
        changes = autodetector.arrange_for_graph(changes, graph)
        # Make sure there's a new name, deps match, etc.
        self.assertEqual(changes["testapp"][0].name, "0003_author")
        self.assertEqual(changes["testapp"][0].dependencies, [("testapp", "0002_foobar")])
        self.assertEqual(changes["otherapp"][0].name, "0002_pony_stable")
        self.assertEqual(changes["otherapp"][0].dependencies, [("otherapp", "0001_initial")])

    def test_trim_apps(self):
        "Tests that trim does not remove dependencies but does remove unwanted apps"
        # Use project state to make a new migration change set
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty, self.other_pony, self.other_stable, self.third_thing])
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner({"ask_initial": True}))
        changes = autodetector.changes()
        # Run through arrange_for_graph
        graph = MigrationGraph()
        changes = autodetector.arrange_for_graph(changes, graph)
        changes["testapp"][0].dependencies.append(("otherapp", "0001_initial"))
        changes = autodetector.trim_to_apps(changes, set(["testapp"]))
        # Make sure there's the right set of migrations
        self.assertEqual(changes["testapp"][0].name, "0001_initial")
        self.assertEqual(changes["otherapp"][0].name, "0001_initial")
        self.assertNotIn("thirdapp", changes)

    def test_new_model(self):
        "Tests autodetection of new models"
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_empty])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector.changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "Author")

    def test_old_model(self):
        "Tests deletion of old models"
        # Make state
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector.changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "DeleteModel")
        self.assertEqual(action.name, "Author")

    def test_add_field(self):
        "Tests autodetection of new fields"
        # Make state
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_name])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector.changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "name")

    def test_remove_field(self):
        "Tests autodetection of removed fields"
        # Make state
        before = self.make_project_state([self.author_name])
        after = self.make_project_state([self.author_empty])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector.changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "name")

    def test_alter_field(self):
        "Tests autodetection of new fields"
        # Make state
        before = self.make_project_state([self.author_name])
        after = self.make_project_state([self.author_name_longer])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector.changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterField")
        self.assertEqual(action.name, "name")

    def test_rename_field(self):
        "Tests autodetection of renamed fields"
        # Make state
        before = self.make_project_state([self.author_name])
        after = self.make_project_state([self.author_name_renamed])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector.changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameField")
        self.assertEqual(action.old_name, "name")
        self.assertEqual(action.new_name, "names")
