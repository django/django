from custom_migration_operations.operations import TestOperation

from django.db import models
from django.db.migrations import operations
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.state import ModelState, ProjectState
from django.db.models import options
from django.db.models.signals import post_autodetect, pre_autodetect
from django.test import TestCase


class CommentBaseOperation(TestOperation):
    """BaseOperation for testing comment operations."""
    def __init__(self, model_name, comment):
        pass


class AddComment(CommentBaseOperation):
    """Operation which should add a comment to a table."""


class RemoveComment(CommentBaseOperation):
    """Operation which should remove a comment from a table."""


def comment_callback(signal, sender):
    """Signal for adding comment operations."""
    for app_label, model_name in sorted(sender.kept_model_keys):
        old_model_name = sender.renamed_models.get((app_label, model_name), model_name)
        old_model_state = sender.from_state.models[app_label, old_model_name]
        new_model_state = sender.to_state.models[app_label, model_name]
        old_comment = old_model_state.options.get('comment', None)
        new_comment = new_model_state.options.get('comment', None)
        if old_comment != new_comment:
            # Operations we need to add
            operations = [(AddComment, new_comment), (RemoveComment, old_comment)]
            for operation, comment in operations:
                if comment is not None:
                    sender.add_operation(app_label, operation(model_name=model_name, comment=comment))


class AutodetectorSignalTests(TestCase):
    """
    Tests the migration autodetector signal.
    """

    author_empty = ModelState("testapp", "Author", [("id", models.AutoField(primary_key=True))])
    author_with_comment_options = ModelState("testapp", "Author", [
        ("id", models.AutoField(primary_key=True)),
    ], {"comment": "Creator of a written work"})
    author_with_new_comment_options = ModelState("testapp", "Author", [
        ("id", models.AutoField(primary_key=True)),
    ], {"comment": "Creator of a book"})

    def setUp(self):
        # Save up the number of connected signals so that we can check at the
        # end that all the signals we register get properly unregistered (#9989)
        self.pre_signals = (
            len(pre_autodetect.receivers),
            len(post_autodetect.receivers)
        )

    def tearDown(self):
        # All our signals got disconnected properly.
        post_signals = (
            len(pre_autodetect.receivers),
            len(post_autodetect.receivers)
        )
        self.assertEqual(self.pre_signals, post_signals)

    def repr_changes(self, changes, include_dependencies=False):
        output = ""
        for app_label, migrations in sorted(changes.items()):
            output += "  %s:\n" % app_label
            for migration in migrations:
                output += "    %s\n" % migration.name
                for operation in migration.operations:
                    output += "      %s\n" % operation
                if include_dependencies:
                    output += "      Dependencies:\n"
                    if migration.dependencies:
                        for dep in migration.dependencies:
                            output += "        %s\n" % (dep,)
                    else:
                        output += "        None\n"
        return output

    def assertNumberMigrations(self, changes, app_label, number):
        if len(changes.get(app_label, [])) != number:
            self.fail("Incorrect number of migrations (%s) for %s (expected %s)\n%s" % (
                len(changes.get(app_label, [])),
                app_label,
                number,
                self.repr_changes(changes),
            ))

    def assertOperationTypes(self, changes, app_label, position, types):
        if not changes.get(app_label):
            self.fail("No migrations found for %s\n%s" % (app_label, self.repr_changes(changes)))
        if len(changes[app_label]) < position + 1:
            self.fail("No migration at index %s for %s\n%s" % (position, app_label, self.repr_changes(changes)))
        migration = changes[app_label][position]
        real_types = [operation.__class__.__name__ for operation in migration.operations]
        if types != real_types:
            self.fail("Operation type mismatch for %s.%s (expected %s):\n%s" % (
                app_label,
                migration.name,
                types,
                self.repr_changes(changes),
            ))

    def make_project_state(self, model_states):
        "Shortcut to make ProjectStates from lists of predefined models"
        project_state = ProjectState()
        for model_state in model_states:
            project_state.add_model(model_state.clone())
        return project_state

    def get_changes(self, before_states, after_states, questioner=None):
        return MigrationAutodetector(
            self.make_project_state(before_states),
            self.make_project_state(after_states),
            questioner,
        )._detect_changes()

    def test_signal_fires(self):
        """Tests autodetection signals fire."""
        fired = {}

        def my_callback1(signal, sender):
            fired['my_callback1'] = True

        def my_callback2(signal, sender):
            fired['my_callback2'] = True
        post_autodetect.connect(my_callback1)
        post_autodetect.connect(my_callback2)
        changes = self.get_changes([self.author_empty], [self.author_empty])
        post_autodetect.disconnect(my_callback1)
        post_autodetect.disconnect(my_callback2)
        self.assertTrue(fired['my_callback1'])
        self.assertTrue(fired['my_callback2'])
        self.assertNumberMigrations(changes, 'testapp', 0)

    def test_add_field_signal(self):
        """Tests autodetection signals can add fields."""
        def add_field_callback(signal, sender):
            field = models.CharField(max_length=200)
            sender.add_operation(
                "testapp",
                operations.AddField(
                    model_name="author",
                    name="name",
                    field=field,
                    preserve_default=field.null,
                ),
                dependencies=[],
            )
        # Signal makes it equivalent to ([self.author_empty], [self.author_name])
        post_autodetect.connect(add_field_callback)
        changes = self.get_changes([self.author_empty], [self.author_empty])
        post_autodetect.disconnect(add_field_callback)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["AddField"])

    def test_no_comment_change_from_options_signal(self):
        """Tests autodetection signals can add fields."""
        # Add a new option
        options.DEFAULT_NAMES = options.DEFAULT_NAMES + ("comment",)
        # Add/Remove comments
        post_autodetect.connect(comment_callback)
        changes = self.get_changes([self.author_with_comment_options], [self.author_with_comment_options])
        post_autodetect.disconnect(comment_callback)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, 'testapp', 0)

    def test_add_comment_from_options_signal(self):
        """Tests autodetection signals can add fields."""
        # Add a new option
        options.DEFAULT_NAMES = options.DEFAULT_NAMES + ("comment",)
        # Add/Remove comments
        post_autodetect.connect(comment_callback)
        changes = self.get_changes([self.author_empty], [self.author_with_comment_options])
        post_autodetect.disconnect(comment_callback)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["AddComment"])

    def test_remove_comment_from_options_signal(self):
        """Tests autodetection signals can add fields."""
        # Add a new option
        options.DEFAULT_NAMES = options.DEFAULT_NAMES + ("comment",)
        # Add/Remove comments
        post_autodetect.connect(comment_callback)
        changes = self.get_changes([self.author_with_comment_options], [self.author_empty])
        post_autodetect.disconnect(comment_callback)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["RemoveComment"])

    def test_alter_comment_from_options_signal(self):
        """Tests autodetection signals can add fields."""
        # Add a new option
        options.DEFAULT_NAMES = options.DEFAULT_NAMES + ("comment",)
        # Add/Remove comments
        post_autodetect.connect(comment_callback)
        changes = self.get_changes([self.author_with_comment_options], [self.author_with_new_comment_options])
        post_autodetect.disconnect(comment_callback)
        # Right number/type of migrations?
        self.assertNumberMigrations(changes, 'testapp', 1)
        self.assertOperationTypes(changes, 'testapp', 0, ["AddComment", "RemoveComment"])
