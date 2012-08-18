from __future__ import absolute_import
import copy
import datetime
from django.test import TestCase
from django.db import connection, DatabaseError, IntegrityError
from django.db.models.fields import IntegerField, TextField, CharField, SlugField
from django.db.models.fields.related import ManyToManyField
from django.db.models.loading import cache
from .models import Author, Book, AuthorWithM2M, Tag, TagUniqueRename, UniqueTest


class SchemaTests(TestCase):
    """
    Tests that the schema-alteration code works correctly.

    Be aware that these tests are more liable than most to false results,
    as sometimes the code to check if a test has worked is almost as complex
    as the code it is testing.
    """

    models = [Author, Book, AuthorWithM2M, Tag, UniqueTest]

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
        connection.disable_constraint_checking()
        for model in self.models:
            # Remove any M2M tables first
            for field in model._meta.local_many_to_many:
                try:
                    cursor.execute("DROP TABLE %s CASCADE" % (
                        connection.ops.quote_name(field.rel.through._meta.db_table),
                    ))
                except DatabaseError:
                    connection.rollback()
                else:
                    connection.commit()
            # Then remove the main tables
            try:
                cursor.execute("DROP TABLE %s CASCADE" % (
                    connection.ops.quote_name(model._meta.db_table),
                ))
            except DatabaseError:
                connection.rollback()
            else:
                connection.commit()
        connection.enable_constraint_checking()
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

    def test_rename(self):
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
        self.assertNotIn("display_name", columns)
        # Alter the name field's name
        new_field = CharField(max_length=254)
        new_field.set_attributes_from_name("display_name")
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
        self.assertEqual(columns['display_name'][0], "CharField")
        self.assertNotIn("name", columns)

    def test_m2m(self):
        """
        Tests adding/removing M2M fields on models
        """
        # Create the tables
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(AuthorWithM2M)
        editor.create_model(Tag)
        editor.commit()
        # Create an M2M field
        new_field = ManyToManyField("schema.Tag", related_name="authors")
        new_field.contribute_to_class(AuthorWithM2M, "tags")
        # Ensure there's no m2m table there
        self.assertRaises(DatabaseError, self.column_classes, new_field.rel.through)
        connection.rollback()
        # Add the field
        editor = connection.schema_editor()
        editor.start()
        editor.create_field(
            Author,
            new_field,
        )
        editor.commit()
        # Ensure there is now an m2m table there
        columns = self.column_classes(new_field.rel.through)
        self.assertEqual(columns['tag_id'][0], "IntegerField")
        # Remove the M2M table again
        editor = connection.schema_editor()
        editor.start()
        editor.delete_field(
            Author,
            new_field,
        )
        editor.commit()
        # Ensure there's no m2m table there
        self.assertRaises(DatabaseError, self.column_classes, new_field.rel.through)
        connection.rollback()

    def test_unique(self):
        """
        Tests removing and adding unique constraints to a single column.
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Tag)
        editor.commit()
        # Ensure the field is unique to begin with
        Tag.objects.create(title="foo", slug="foo")
        self.assertRaises(IntegrityError, Tag.objects.create, title="bar", slug="foo")
        connection.rollback()
        # Alter the slug field to be non-unique
        new_field = SlugField(unique=False)
        new_field.set_attributes_from_name("slug")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Tag,
            Tag._meta.get_field_by_name("slug")[0],
            new_field,
        )
        editor.commit()
        # Ensure the field is no longer unique
        Tag.objects.create(title="foo", slug="foo")
        Tag.objects.create(title="bar", slug="foo")
        connection.rollback()
        # Alter the slug field to be non-unique
        new_new_field = SlugField(unique=True)
        new_new_field.set_attributes_from_name("slug")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Tag,
            new_field,
            new_new_field,
        )
        editor.commit()
        # Ensure the field is unique again
        Tag.objects.create(title="foo", slug="foo")
        self.assertRaises(IntegrityError, Tag.objects.create, title="bar", slug="foo")
        connection.rollback()
        # Rename the field
        new_field = SlugField(unique=False)
        new_field.set_attributes_from_name("slug2")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Tag,
            Tag._meta.get_field_by_name("slug")[0],
            TagUniqueRename._meta.get_field_by_name("slug2")[0],
        )
        editor.commit()
        # Ensure the field is still unique
        TagUniqueRename.objects.create(title="foo", slug2="foo")
        self.assertRaises(IntegrityError, TagUniqueRename.objects.create, title="bar", slug2="foo")
        connection.rollback()

    def test_unique_together(self):
        """
        Tests removing and adding unique_together constraints on a model.
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(UniqueTest)
        editor.commit()
        # Ensure the fields are unique to begin with
        UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.create(year=2011, slug="foo")
        UniqueTest.objects.create(year=2011, slug="bar")
        self.assertRaises(IntegrityError, UniqueTest.objects.create, year=2012, slug="foo")
        connection.rollback()
        # Alter the model to it's non-unique-together companion
        editor = connection.schema_editor()
        editor.start()
        editor.alter_unique_together(
            UniqueTest,
            UniqueTest._meta.unique_together,
            [],
        )
        editor.commit()
        # Ensure the fields are no longer unique
        UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.create(year=2012, slug="foo")
        connection.rollback()
        # Alter it back
        new_new_field = SlugField(unique=True)
        new_new_field.set_attributes_from_name("slug")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_unique_together(
            UniqueTest,
            [],
            UniqueTest._meta.unique_together,
        )
        editor.commit()
        # Ensure the fields are unique again
        UniqueTest.objects.create(year=2012, slug="foo")
        self.assertRaises(IntegrityError, UniqueTest.objects.create, year=2012, slug="foo")
        connection.rollback()

    def test_db_table(self):
        """
        Tests renaming of the table
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.commit()
        # Ensure the table is there to begin with
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        # Alter the table
        editor = connection.schema_editor()
        editor.start()
        editor.alter_db_table(
            Author,
            "schema_author",
            "schema_otherauthor",
        )
        editor.commit()
        # Ensure the table is there afterwards
        Author._meta.db_table = "schema_otherauthor"
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        # Alter the table again
        editor = connection.schema_editor()
        editor.start()
        editor.alter_db_table(
            Author,
            "schema_otherauthor",
            "schema_author",
        )
        editor.commit()
        # Ensure the table is still there
        Author._meta.db_table = "schema_author"
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
