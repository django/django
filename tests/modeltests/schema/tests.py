from __future__ import absolute_import
import copy
import datetime
from django.test import TestCase
from django.db.models.loading import cache
from django.db import connection, DatabaseError, IntegrityError
from .models import Author, Book


class SchemaTests(TestCase):
    """
    Tests that the schema-alteration code works correctly.

    Be aware that these tests are more liable than most to false results,
    as sometimes the code to check if a test has worked is almost as complex
    as the code it is testing.
    """

    models = [Author, Book]

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
