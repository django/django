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
    author_with_book = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("book", models.ForeignKey("otherapp.Book"))])
    author_proxy = ModelState("testapp", "AuthorProxy", [], {"proxy": True}, ("testapp.author", ))
    author_proxy_notproxy = ModelState("testapp", "AuthorProxy", [], {}, ("testapp.author", ))
    other_pony = ModelState("otherapp", "Pony", [("id", models.AutoField(primary_key=True))])
    other_stable = ModelState("otherapp", "Stable", [("id", models.AutoField(primary_key=True))])
    third_thing = ModelState("thirdapp", "Thing", [("id", models.AutoField(primary_key=True))])
    book = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))])
    book_unique = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": [("author", "title")]})
    book_unique_2 = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": [("title", "author")]})
    edition = ModelState("thirdapp", "Edition", [("id", models.AutoField(primary_key=True)), ("book", models.ForeignKey("otherapp.Book"))])

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
        changes = autodetector._detect_changes()
        # Run through arrange_for_graph
        changes = autodetector._arrange_for_graph(changes, graph)
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
        changes = autodetector._detect_changes()
        # Run through arrange_for_graph
        graph = MigrationGraph()
        changes = autodetector._arrange_for_graph(changes, graph)
        changes["testapp"][0].dependencies.append(("otherapp", "0001_initial"))
        changes = autodetector._trim_to_apps(changes, set(["testapp"]))
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
        changes = autodetector._detect_changes()
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
        changes = autodetector._detect_changes()
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
        changes = autodetector._detect_changes()
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
        changes = autodetector._detect_changes()
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
        changes = autodetector._detect_changes()
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
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner({"ask_rename": True}))
        changes = autodetector._detect_changes()
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

    def test_fk_dependency(self):
        "Tests that having a ForeignKey automatically adds a dependency"
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_name, self.book, self.edition])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        self.assertEqual(len(changes['otherapp']), 1)
        self.assertEqual(len(changes['thirdapp']), 1)
        # Right number of actions?
        migration1 = changes['testapp'][0]
        self.assertEqual(len(migration1.operations), 1)
        migration2 = changes['otherapp'][0]
        self.assertEqual(len(migration2.operations), 1)
        migration3 = changes['thirdapp'][0]
        self.assertEqual(len(migration3.operations), 1)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration2.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration3.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [])
        self.assertEqual(migration2.dependencies, [("testapp", "auto_1")])
        self.assertEqual(migration3.dependencies, [("otherapp", "auto_1")])

    def test_circular_fk_dependency(self):
        """
        Tests that having a circular ForeignKey dependency automatically
        resolves the situation into 2 migrations on one side and 1 on the other.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_book, self.book])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        self.assertEqual(len(changes['otherapp']), 2)
        # Right number of actions?
        migration1 = changes['testapp'][0]
        self.assertEqual(len(migration1.operations), 1)
        migration2 = changes['otherapp'][0]
        self.assertEqual(len(migration2.operations), 1)
        migration3 = changes['otherapp'][1]
        self.assertEqual(len(migration2.operations), 1)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration2.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(len(action.fields), 2)
        action = migration3.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "author")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [("otherapp", "auto_1")])
        self.assertEqual(migration2.dependencies, [])
        self.assertEqual(set(migration3.dependencies), set([("otherapp", "auto_1"), ("testapp", "auto_1")]))

    def test_unique_together(self):
        "Tests unique_together detection"
        # Make state
        before = self.make_project_state([self.author_empty, self.book])
        after = self.make_project_state([self.author_empty, self.book_unique])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action.name, "book")
        self.assertEqual(action.unique_together, set([("author", "title")]))

    def test_unique_together_ordering(self):
        "Tests that unique_together also triggers on ordering changes"
        # Make state
        before = self.make_project_state([self.author_empty, self.book_unique])
        after = self.make_project_state([self.author_empty, self.book_unique_2])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action.name, "book")
        self.assertEqual(action.unique_together, set([("title", "author")]))

    def test_proxy_ignorance(self):
        "Tests that the autodetector correctly ignores proxy models"
        # First, we test adding a proxy model
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_empty, self.author_proxy])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes), 0)

        # Now, we test turning a proxy model into a non-proxy model
        before = self.make_project_state([self.author_empty, self.author_proxy])
        after = self.make_project_state([self.author_empty, self.author_proxy_notproxy])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "AuthorProxy")
