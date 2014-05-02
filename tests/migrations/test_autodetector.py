# encoding: utf8
from django.test import TestCase, override_settings
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.questioner import MigrationQuestioner
from django.db.migrations.state import ProjectState, ModelState
from django.db.migrations.graph import MigrationGraph
from django.db import models


class DeconstructableObject(object):
    """
    A custom deconstructable object.
    """

    def deconstruct(self):
        return self.__module__ + '.' + self.__class__.__name__, [], {}


class AutodetectorTests(TestCase):
    """
    Tests the migration autodetector.
    """

    author_empty = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True))])
    author_name = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200))])
    author_name_longer = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=400))])
    author_name_renamed = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("names", models.CharField(max_length=200))])
    author_name_default = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default='Ada Lovelace'))])
    author_name_deconstructable_1 = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default=DeconstructableObject()))])
    author_name_deconstructable_2 = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200, default=DeconstructableObject()))])
    author_with_book = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("book", models.ForeignKey("otherapp.Book"))])
    author_renamed_with_book = ModelState("testapp", "Writer", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("book", models.ForeignKey("otherapp.Book"))])
    author_with_publisher_string = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("publisher_name", models.CharField(max_length=200))])
    author_with_publisher = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("publisher", models.ForeignKey("testapp.Publisher"))])
    author_with_custom_user = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=200)), ("user", models.ForeignKey("thirdapp.CustomUser"))])
    author_proxy = ModelState("testapp", "AuthorProxy", [], {"proxy": True}, ("testapp.author", ))
    author_proxy_notproxy = ModelState("testapp", "AuthorProxy", [], {}, ("testapp.author", ))
    author_unmanaged = ModelState("testapp", "AuthorUnmanaged", [], {"managed": False}, ("testapp.author", ))
    author_unmanaged_managed = ModelState("testapp", "AuthorUnmanaged", [], {}, ("testapp.author", ))
    publisher = ModelState("testapp", "Publisher", [("id", models.AutoField(primary_key=True)), ("name", models.CharField(max_length=100))])
    publisher_with_author = ModelState("testapp", "Publisher", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("name", models.CharField(max_length=100))])
    publisher_with_book = ModelState("testapp", "Publisher", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("otherapp.Book")), ("name", models.CharField(max_length=100))])
    other_pony = ModelState("otherapp", "Pony", [("id", models.AutoField(primary_key=True))])
    other_stable = ModelState("otherapp", "Stable", [("id", models.AutoField(primary_key=True))])
    third_thing = ModelState("thirdapp", "Thing", [("id", models.AutoField(primary_key=True))])
    book = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))])
    book_with_no_author = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("title", models.CharField(max_length=200))])
    book_with_author_renamed = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Writer")), ("title", models.CharField(max_length=200))])
    book_with_field_and_author_renamed = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("writer", models.ForeignKey("testapp.Writer")), ("title", models.CharField(max_length=200))])
    book_with_multiple_authors = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("authors", models.ManyToManyField("testapp.Author")), ("title", models.CharField(max_length=200))])
    book_with_multiple_authors_through_attribution = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("authors", models.ManyToManyField("testapp.Author", through="otherapp.Attribution")), ("title", models.CharField(max_length=200))])
    book_unique = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": [("author", "title")]})
    book_unique_2 = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": [("title", "author")]})
    book_unique_3 = ModelState("otherapp", "Book", [("id", models.AutoField(primary_key=True)), ("newfield", models.IntegerField()), ("author", models.ForeignKey("testapp.Author")), ("title", models.CharField(max_length=200))], {"unique_together": [("title", "newfield")]})
    attribution = ModelState("otherapp", "Attribution", [("id", models.AutoField(primary_key=True)), ("author", models.ForeignKey("testapp.Author")), ("book", models.ForeignKey("otherapp.Book"))])
    edition = ModelState("thirdapp", "Edition", [("id", models.AutoField(primary_key=True)), ("book", models.ForeignKey("otherapp.Book"))])
    custom_user = ModelState("thirdapp", "CustomUser", [("id", models.AutoField(primary_key=True)), ("username", models.CharField(max_length=255))])
    knight = ModelState("eggs", "Knight", [("id", models.AutoField(primary_key=True))])
    rabbit = ModelState("eggs", "Rabbit", [("id", models.AutoField(primary_key=True)), ("knight", models.ForeignKey("eggs.Knight")), ("parent", models.ForeignKey("eggs.Rabbit"))], {"unique_together": [("parent", "knight")]})

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
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner(defaults={"ask_initial": True}))
        changes = autodetector._detect_changes()
        # Run through arrange_for_graph
        graph = MigrationGraph()
        changes = autodetector.arrange_for_graph(changes, graph)
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

    def test_rename_model(self):
        "Tests autodetection of renamed models"
        # Make state
        before = self.make_project_state([self.author_with_book, self.book])
        after = self.make_project_state([self.author_renamed_with_book, self.book_with_author_renamed])
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner({"ask_rename_model": True}))
        changes = autodetector._detect_changes()

        # Right number of migrations for model rename?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameModel")
        self.assertEqual(action.old_name, "Author")
        self.assertEqual(action.new_name, "Writer")

        # Right number of migrations for related field rename?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right action?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "AlterField")
        self.assertEqual(action.name, "author")
        self.assertEqual(action.field.rel.to.__name__, "Writer")

    def test_rename_model_with_renamed_rel_field(self):
        """
        Tests autodetection of renamed models while simultaneously renaming one
        of the fields that relate to the renamed model.
        """
        # Make state
        before = self.make_project_state([self.author_with_book, self.book])
        after = self.make_project_state([self.author_renamed_with_book, self.book_with_field_and_author_renamed])
        autodetector = MigrationAutodetector(before, after, MigrationQuestioner({"ask_rename_model": True, "ask_rename": True}))
        changes = autodetector._detect_changes()

        # Right number of migrations for model rename?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 1)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameModel")
        self.assertEqual(action.old_name, "Author")
        self.assertEqual(action.new_name, "Writer")

        # Right number of migrations for related field rename?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RenameField")
        self.assertEqual(action.old_name, "author")
        self.assertEqual(action.new_name, "writer")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "AlterField")
        self.assertEqual(action.name, "writer")
        self.assertEqual(action.field.rel.to.__name__, "Writer")

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

    def test_same_app_no_fk_dependency(self):
        """
        Tests that a migration with a FK between two models of the same app
        does not have a dependency to itself.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_publisher, self.publisher])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        # Right dependencies?
        self.assertEqual(migration.dependencies, [])

    def test_circular_fk_dependency(self):
        """
        Tests that having a circular ForeignKey dependency automatically
        resolves the situation into 2 migrations on one side and 1 on the other.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_book, self.book, self.publisher_with_book])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        self.assertEqual(len(changes['otherapp']), 2)
        # Right number of actions?
        migration1 = changes['testapp'][0]
        self.assertEqual(len(migration1.operations), 2)
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
        self.assertEqual(migration2.dependencies, [('testapp', '__first__')])
        self.assertEqual(set(migration3.dependencies), set([("otherapp", "auto_1"), ("testapp", "auto_1")]))

    def test_same_app_circular_fk_dependency(self):
        """
        Tests that a migration with a FK between two models of the same app
        does not have a dependency to itself.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.author_with_publisher, self.publisher_with_author])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 2)
        # Right number of actions?
        migration1 = changes['testapp'][0]
        self.assertEqual(len(migration1.operations), 2)
        migration2 = changes['testapp'][1]
        self.assertEqual(len(migration2.operations), 1)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration1.operations[1]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration2.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "publisher")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [])
        self.assertEqual(migration2.dependencies, [("testapp", "auto_1")])

    def test_same_app_circular_fk_dependency_and_unique_together(self):
        """
        Tests that a migration with circular FK dependency does not try to
        create unique together constraint before creating all required fields first.
        See ticket #22275.
        """
        # Make state
        before = self.make_project_state([])
        after = self.make_project_state([self.knight, self.rabbit])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['eggs']), 2)
        # Right number of actions?
        migration1 = changes['eggs'][0]
        self.assertEqual(len(migration1.operations), 2)
        migration2 = changes['eggs'][1]
        self.assertEqual(len(migration2.operations), 2)
        # Right actions?
        action = migration1.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        action = migration1.operations[1]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        # CreateModel action for Rabbit should not have unique_together now
        self.assertEqual(action.name, "Rabbit")
        self.assertFalse("unique_together" in action.options)
        action = migration2.operations[0]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "parent")
        action = migration2.operations[1]
        self.assertEqual(action.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action.name, "rabbit")
        # Right dependencies?
        self.assertEqual(migration1.dependencies, [])
        self.assertEqual(migration2.dependencies, [("eggs", "auto_1")])

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

    def test_add_field_and_unique_together(self):
        "Tests that added fields will be created before using them in unique together"
        before = self.make_project_state([self.author_empty, self.book])
        after = self.make_project_state([self.author_empty, self.book_unique_3])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions order?
        action1 = migration.operations[0]
        action2 = migration.operations[1]
        self.assertEqual(action1.__class__.__name__, "AddField")
        self.assertEqual(action2.__class__.__name__, "AlterUniqueTogether")
        self.assertEqual(action2.unique_together, set([("title", "newfield")]))

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

    def test_unmanaged_ignorance(self):
        "Tests that the autodetector correctly ignores managed models"
        # First, we test adding an unmanaged model
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_empty, self.author_unmanaged])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes), 0)

        # Now, we test turning an unmanaged model into a managed model
        before = self.make_project_state([self.author_empty, self.author_unmanaged])
        after = self.make_project_state([self.author_empty, self.author_unmanaged_managed])
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
        self.assertEqual(action.name, "AuthorUnmanaged")

    @override_settings(AUTH_USER_MODEL="thirdapp.CustomUser")
    def test_swappable(self):
        before = self.make_project_state([self.custom_user])
        after = self.make_project_state([self.custom_user, self.author_with_custom_user])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes), 1)
        # Check the dependency is correct
        migration = changes['testapp'][0]
        self.assertEqual(migration.dependencies, [("__setting__", "AUTH_USER_MODEL")])

    def test_add_field_with_default(self):
        """
        Adding a field with a default should work (#22030).
        """
        # Make state
        before = self.make_project_state([self.author_empty])
        after = self.make_project_state([self.author_name_default])
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

    def test_custom_deconstructable(self):
        """
        Two instances which deconstruct to the same value aren't considered a
        change.
        """
        before = self.make_project_state([self.author_name_deconstructable_1])
        after = self.make_project_state([self.author_name_deconstructable_2])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        self.assertEqual(changes, {})

    def test_replace_string_with_foreignkey(self):
        """
        Adding an FK in the same "spot" as a deleted CharField should work. (#22300).
        """
        # Make state
        before = self.make_project_state([self.author_with_publisher_string])
        after = self.make_project_state([self.author_with_publisher, self.publisher])
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 3)
        # Right actions?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "CreateModel")
        self.assertEqual(action.name, "Publisher")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "AddField")
        self.assertEqual(action.name, "publisher")
        action = migration.operations[2]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "publisher_name")

    def test_foreign_key_removed_before_target_model(self):
        """
        Removing an FK and the model it targets in the same change must remove
        the FK field before the model to maintain consistency.
        """
        before = self.make_project_state([self.author_with_publisher, self.publisher])
        after = self.make_project_state([self.author_name])  # removes both the model and FK
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['testapp']), 1)
        # Right number of actions?
        migration = changes['testapp'][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions in right order?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "publisher")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "DeleteModel")
        self.assertEqual(action.name, "Publisher")

    def test_many_to_many_removed_before_through_model(self):
        """
        Removing a ManyToManyField and the "through" model in the same change must remove
        the field before the model to maintain consistency.
        """
        before = self.make_project_state([self.book_with_multiple_authors_through_attribution, self.author_name, self.attribution])
        after = self.make_project_state([self.book_with_no_author, self.author_name])  # removes both the through model and ManyToMany
        autodetector = MigrationAutodetector(before, after)
        changes = autodetector._detect_changes()
        # Right number of migrations?
        self.assertEqual(len(changes['otherapp']), 1)
        # Right number of actions?
        migration = changes['otherapp'][0]
        self.assertEqual(len(migration.operations), 2)
        # Right actions in right order?
        action = migration.operations[0]
        self.assertEqual(action.__class__.__name__, "RemoveField")
        self.assertEqual(action.name, "authors")
        action = migration.operations[1]
        self.assertEqual(action.__class__.__name__, "DeleteModel")
        self.assertEqual(action.name, "Attribution")
