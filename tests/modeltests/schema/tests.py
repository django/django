from __future__ import absolute_import
import copy
import datetime
from django.test import TestCase
from django.db import connection, DatabaseError, IntegrityError
from django.db.models.fields import IntegerField, TextField
from django.db.models.loading import cache
from .models import Author, Book


class SchemaTests(TestCase):
    """
    Tests that the schema-alteration code works correctly.

    Be aware that these tests are more liable than most to false results,
    as sometimes the code to check if a test has worked is almost as complex
    as the code it is testing.
    """

    models = [Author, Book]

    # Utility functions

    def setUp(self):
        # Make sure we're in manual transaction mode
        connection.commit_unless_managed()
        connection.enter_transaction_management()
        connection.managed(True)
        # The unmanaged models need to be removed after the test in order to
        # prevent bad interactions with the flush operation in other tests.
        self.old_app_models = copy.deepcopy(cache.app_models)
        self.old_app_store = copy.deepcopy(cache.app_store)
        for model in self.models:
            model._meta.managed = True

    def tearDown(self):
        # Rollback anything that may have happened
        connection.rollback()
        # Delete any tables made for our models
        cursor = connection.cursor()
        for model in self.models:
            try:
                cursor.execute("DROP TABLE %s CASCADE" % (
                    connection.ops.quote_name(model._meta.db_table),
                ))
            except DatabaseError:
                connection.rollback()
            else:
                connection.commit()
        # Unhook our models
        for model in self.models:
            model._meta.managed = False
        cache.app_models = self.old_app_models
        cache.app_store = self.old_app_store
        cache._get_models_cache = {}

    def column_classes(self, model):
        cursor = connection.cursor()
        return dict(
            (d[0], (connection.introspection.get_field_type(d[1], d), d))
            for d in connection.introspection.get_table_description(
                cursor,
                model._meta.db_table,
            )
        )

    # Tests

    def test_creation_deletion(self):
        """
        Tries creating a model's table, and then deleting it.
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.commit()
        # Check that it's there
        try:
            list(Author.objects.all())
        except DatabaseError, e:
            self.fail("Table not created: %s" % e)
        # Clean up that table
        editor.start()
        editor.delete_model(Author)
        editor.commit()
        # Check that it's gone
        self.assertRaises(
            DatabaseError,
            lambda: list(Author.objects.all()),
        )

    def test_creation_fk(self):
        "Tests that creating tables out of FK order works"
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Book)
        editor.create_model(Author)
        editor.commit()
        # Check that both tables are there
        try:
            list(Author.objects.all())
        except DatabaseError, e:
            self.fail("Author table not created: %s" % e)
        try:
            list(Book.objects.all())
        except DatabaseError, e:
            self.fail("Book table not created: %s" % e)
        # Make sure the FK constraint is present
        with self.assertRaises(IntegrityError):
            Book.objects.create(
                author_id = 1,
                title = "Much Ado About Foreign Keys",
                pub_date = datetime.datetime.now(),
            )
            connection.commit()

    def test_create_field(self):
        """
        Tests adding fields to models
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.commit()
        # Ensure there's no age field
        columns = self.column_classes(Author)
        self.assertNotIn("age", columns)
        # Alter the name field to a TextField
        new_field = IntegerField(null=True)
        new_field.set_attributes_from_name("age")
        editor = connection.schema_editor()
        editor.start()
        editor.create_field(
            Author,
            new_field,
        )
        editor.commit()
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['age'][0], "IntegerField")
        self.assertEqual(columns['age'][1][6], True)

    def test_alter(self):
        """
        Tests simple altering of fields
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.commit()
        # Ensure the field is right to begin with
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        self.assertEqual(columns['name'][1][3], 255)
        self.assertEqual(columns['name'][1][6], False)
        # Alter the name field to a TextField
        new_field = TextField(null=True)
        new_field.set_attributes_from_name("name")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Author,
            Author._meta.get_field_by_name("name")[0],
            new_field,
        )
        editor.commit()
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "TextField")
        self.assertEqual(columns['name'][1][6], True)
