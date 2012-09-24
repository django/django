from __future__ import absolute_import
import copy
import datetime
from django.test import TestCase
from django.utils.unittest import skipUnless
from django.db import connection, DatabaseError, IntegrityError
from django.db.models.fields import IntegerField, TextField, CharField, SlugField
from django.db.models.fields.related import ManyToManyField, ForeignKey
from django.db.models.loading import cache, default_cache, AppCache
from .models import Author, AuthorWithM2M, Book, BookWithSlug, BookWithM2M, Tag, TagUniqueRename, UniqueTest


class SchemaTests(TestCase):
    """
    Tests that the schema-alteration code works correctly.

    Be aware that these tests are more liable than most to false results,
    as sometimes the code to check if a test has worked is almost as complex
    as the code it is testing.
    """

    models = [Author, AuthorWithM2M, Book, BookWithSlug, BookWithM2M, Tag, TagUniqueRename, UniqueTest]

    # Utility functions

    def setUp(self):
        # Make sure we're in manual transaction mode
        connection.commit_unless_managed()
        connection.enter_transaction_management()
        connection.managed(True)
        # The unmanaged models need to be removed after the test in order to
        # prevent bad interactions with the flush operation in other tests.
        self.app_cache = AppCache()
        cache.set_cache(self.app_cache)
        cache.copy_from(default_cache)
        for model in self.models:
            cache.register_models("schema", model)
            model._prepare()

    def tearDown(self):
        # Delete any tables made for our models
        self.delete_tables()
        # Rollback anything that may have happened
        connection.rollback()
        connection.leave_transaction_management()
        cache.set_cache(default_cache)
        cache.app_models['schema'] = {}  # One M2M gets left in the old cache

    def delete_tables(self):
        "Deletes all model tables for our models for a clean test environment"
        cursor = connection.cursor()
        connection.disable_constraint_checking()
        for model in self.models:
            # Remove any M2M tables first
            for field in model._meta.local_many_to_many:
                try:
                    cursor.execute(connection.schema_editor().sql_delete_table % {
                        "table": connection.ops.quote_name(field.rel.through._meta.db_table),
                    })
                except DatabaseError:
                    connection.rollback()
                else:
                    connection.commit()
            # Then remove the main tables
            try:
                cursor.execute(connection.schema_editor().sql_delete_table % {
                    "table": connection.ops.quote_name(model._meta.db_table),
                })
            except DatabaseError:
                connection.rollback()
            else:
                connection.commit()
        connection.enable_constraint_checking()

    def column_classes(self, model):
        cursor = connection.cursor()
        columns = dict(
            (d[0], (connection.introspection.get_field_type(d[1], d), d))
            for d in connection.introspection.get_table_description(
                cursor,
                model._meta.db_table,
            )
        )
        # SQLite has a different format for field_type
        for name, (type, desc) in columns.items():
            if isinstance(type, tuple):
                columns[name] = (type[0], desc)
        # SQLite also doesn't error properly
        if not columns:
            raise DatabaseError("Table does not exist (empty pragma)")
        return columns

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
        list(Author.objects.all())
        # Clean up that table
        editor.start()
        editor.delete_model(Author)
        editor.commit()
        # Check that it's gone
        self.assertRaises(
            DatabaseError,
            lambda: list(Author.objects.all()),
        )

    @skipUnless(connection.features.supports_foreign_keys, "No FK support")
    def test_fk(self):
        "Tests that creating tables out of FK order, then repointing, works"
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Book)
        editor.create_model(Author)
        editor.create_model(Tag)
        editor.commit()
        # Check that initial tables are there
        list(Author.objects.all())
        list(Book.objects.all())
        # Make sure the FK constraint is present
        with self.assertRaises(IntegrityError):
            Book.objects.create(
                author_id = 1,
                title = "Much Ado About Foreign Keys",
                pub_date = datetime.datetime.now(),
            )
            connection.commit()
        # Repoint the FK constraint
        new_field = ForeignKey(Tag)
        new_field.set_attributes_from_name("author")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Book,
            Book._meta.get_field_by_name("author")[0],
            new_field,
            strict=True,
        )
        editor.commit()
        # Make sure the new FK constraint is present
        constraints = connection.introspection.get_constraints(connection.cursor(), Book._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == set(["author_id"]) and details['foreign_key']:
                self.assertEqual(details['foreign_key'], ('schema_tag', 'id'))
                break
        else:
            self.fail("No FK constraint for author_id found")

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
            strict=True,
        )
        editor.commit()
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "TextField")
        self.assertEqual(columns['name'][1][6], True)
        # Change nullability again
        new_field2 = TextField(null=False)
        new_field2.set_attributes_from_name("name")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Author,
            new_field,
            new_field2,
            strict=True,
        )
        editor.commit()
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "TextField")
        self.assertEqual(columns['name'][1][6], False)

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
            strict = True,
        )
        editor.commit()
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['display_name'][0], "CharField")
        self.assertNotIn("name", columns)

    def test_m2m_create(self):
        """
        Tests M2M fields on models during creation
        """
        # Create the tables
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.create_model(Tag)
        editor.create_model(BookWithM2M)
        editor.commit()
        # Ensure there is now an m2m table there
        columns = self.column_classes(BookWithM2M._meta.get_field_by_name("tags")[0].rel.through)
        self.assertEqual(columns['tag_id'][0], "IntegerField")

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
        try:
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
        finally:
            # Cleanup model states
            AuthorWithM2M._meta.local_many_to_many.remove(new_field)
            del AuthorWithM2M._meta._m2m_cache

    def test_m2m_repoint(self):
        """
        Tests repointing M2M fields
        """
        # Create the tables
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.create_model(BookWithM2M)
        editor.create_model(Tag)
        editor.create_model(UniqueTest)
        editor.commit()
        # Ensure the M2M exists and points to Tag
        constraints = connection.introspection.get_constraints(connection.cursor(), BookWithM2M._meta.get_field_by_name("tags")[0].rel.through._meta.db_table)
        if connection.features.supports_foreign_keys:
            for name, details in constraints.items():
                if details['columns'] == set(["tag_id"]) and details['foreign_key']:
                    self.assertEqual(details['foreign_key'], ('schema_tag', 'id'))
                    break
            else:
                self.fail("No FK constraint for tag_id found")
        # Repoint the M2M
        new_field = ManyToManyField(UniqueTest)
        new_field.contribute_to_class(BookWithM2M, "uniques")
        try:
            editor = connection.schema_editor()
            editor.start()
            editor.alter_field(
                Author,
                BookWithM2M._meta.get_field_by_name("tags")[0],
                new_field,
            )
            editor.commit()
            # Ensure old M2M is gone
            self.assertRaises(DatabaseError, self.column_classes, BookWithM2M._meta.get_field_by_name("tags")[0].rel.through)
            connection.rollback()
            # Ensure the new M2M exists and points to UniqueTest
            constraints = connection.introspection.get_constraints(connection.cursor(), new_field.rel.through._meta.db_table)
            if connection.features.supports_foreign_keys:
                for name, details in constraints.items():
                    if details['columns'] == set(["uniquetest_id"]) and details['foreign_key']:
                        self.assertEqual(details['foreign_key'], ('schema_uniquetest', 'id'))
                        break
                else:
                    self.fail("No FK constraint for tag_id found")
        finally:
            # Cleanup model states
            BookWithM2M._meta.local_many_to_many.remove(new_field)
            del BookWithM2M._meta._m2m_cache

    @skipUnless(connection.features.supports_check_constraints, "No check constraints")
    def test_check_constraints(self):
        """
        Tests creating/deleting CHECK constraints
        """
        # Create the tables
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.commit()
        # Ensure the constraint exists
        constraints = connection.introspection.get_constraints(connection.cursor(), Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == set(["height"]) and details['check']:
                break
        else:
            self.fail("No check constraint for height found")
        # Alter the column to remove it
        new_field = IntegerField(null=True, blank=True)
        new_field.set_attributes_from_name("height")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Author,
            Author._meta.get_field_by_name("height")[0],
            new_field,
            strict = True,
        )
        editor.commit()
        constraints = connection.introspection.get_constraints(connection.cursor(), Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == set(["height"]) and details['check']:
                self.fail("Check constraint for height found")
        # Alter the column to re-add it
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Author,
            new_field,
            Author._meta.get_field_by_name("height")[0],
            strict = True,
        )
        editor.commit()
        constraints = connection.introspection.get_constraints(connection.cursor(), Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == set(["height"]) and details['check']:
                break
        else:
            self.fail("No check constraint for height found")

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
            strict = True,
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
            strict = True,
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
            strict = True,
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

    def test_indexes(self):
        """
        Tests creation/altering of indexes
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Author)
        editor.create_model(Book)
        editor.commit()
        # Ensure the table is there and has the right index
        self.assertIn(
            "title",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Alter to remove the index
        new_field = CharField(max_length=100, db_index=False)
        new_field.set_attributes_from_name("title")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Book,
            Book._meta.get_field_by_name("title")[0],
            new_field,
            strict = True,
        )
        editor.commit()
        # Ensure the table is there and has no index
        self.assertNotIn(
            "title",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Alter to re-add the index
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            Book,
            new_field,
            Book._meta.get_field_by_name("title")[0],
            strict = True,
        )
        editor.commit()
        # Ensure the table is there and has the index again
        self.assertIn(
            "title",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Add a unique column, verify that creates an implicit index
        editor = connection.schema_editor()
        editor.start()
        editor.create_field(
            Book,
            BookWithSlug._meta.get_field_by_name("slug")[0],
        )
        editor.commit()
        self.assertIn(
            "slug",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Remove the unique, check the index goes with it
        new_field2 = CharField(max_length=20, unique=False)
        new_field2.set_attributes_from_name("slug")
        editor = connection.schema_editor()
        editor.start()
        editor.alter_field(
            BookWithSlug,
            BookWithSlug._meta.get_field_by_name("slug")[0],
            new_field2,
            strict = True,
        )
        editor.commit()
        self.assertNotIn(
            "slug",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )

    def test_primary_key(self):
        """
        Tests altering of the primary key
        """
        # Create the table
        editor = connection.schema_editor()
        editor.start()
        editor.create_model(Tag)
        editor.commit()
        # Ensure the table is there and has the right PK
        self.assertTrue(
            connection.introspection.get_indexes(connection.cursor(), Tag._meta.db_table)['id']['primary_key'],
        )
        # Alter to change the PK
        new_field = SlugField(primary_key=True)
        new_field.set_attributes_from_name("slug")
        editor = connection.schema_editor()
        editor.start()
        editor.delete_field(Tag, Tag._meta.get_field_by_name("id")[0])
        editor.alter_field(
            Tag,
            Tag._meta.get_field_by_name("slug")[0],
            new_field,
        )
        editor.commit()
        # Ensure the PK changed
        self.assertNotIn(
            'id',
            connection.introspection.get_indexes(connection.cursor(), Tag._meta.db_table),
        )
        self.assertTrue(
            connection.introspection.get_indexes(connection.cursor(), Tag._meta.db_table)['slug']['primary_key'],
        )
