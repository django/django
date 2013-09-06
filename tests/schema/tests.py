from __future__ import absolute_import
import datetime
import unittest

from django.test import TransactionTestCase
from django.db import connection, DatabaseError, IntegrityError
from django.db.models.fields import IntegerField, TextField, CharField, SlugField
from django.db.models.fields.related import ManyToManyField, ForeignKey
from django.db.transaction import atomic
from .models import Author, AuthorWithM2M, Book, BookWithSlug, BookWithM2M, Tag, TagIndexed, TagM2MTest, TagUniqueRename, UniqueTest


class SchemaTests(TransactionTestCase):
    """
    Tests that the schema-alteration code works correctly.

    Be aware that these tests are more liable than most to false results,
    as sometimes the code to check if a test has worked is almost as complex
    as the code it is testing.
    """

    available_apps = []

    models = [Author, AuthorWithM2M, Book, BookWithSlug, BookWithM2M, Tag, TagIndexed, TagM2MTest, TagUniqueRename, UniqueTest]

    # Utility functions

    def tearDown(self):
        # Delete any tables made for our models
        self.delete_tables()

    def delete_tables(self):
        "Deletes all model tables for our models for a clean test environment"
        cursor = connection.cursor()
        connection.disable_constraint_checking()
        table_names = connection.introspection.table_names(cursor)
        for model in self.models:
            # Remove any M2M tables first
            for field in model._meta.local_many_to_many:
                with atomic():
                    tbl = field.rel.through._meta.db_table
                    if tbl in table_names:
                        cursor.execute(connection.schema_editor().sql_delete_table % {
                            "table": connection.ops.quote_name(tbl),
                        })
                        table_names.remove(tbl)
            # Then remove the main tables
            with atomic():
                tbl = model._meta.db_table
                if tbl in table_names:
                    cursor.execute(connection.schema_editor().sql_delete_table % {
                        "table": connection.ops.quote_name(tbl),
                    })
                    table_names.remove(tbl)
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
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Check that it's there
        list(Author.objects.all())
        # Clean up that table
        with connection.schema_editor() as editor:
            editor.delete_model(Author)
        # Check that it's gone
        self.assertRaises(
            DatabaseError,
            lambda: list(Author.objects.all()),
        )

    @unittest.skipUnless(connection.features.supports_foreign_keys, "No FK support")
    def test_fk(self):
        "Tests that creating tables out of FK order, then repointing, works"
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Book)
            editor.create_model(Author)
            editor.create_model(Tag)
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
        # Repoint the FK constraint
        new_field = ForeignKey(Tag)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Book,
                Book._meta.get_field_by_name("author")[0],
                new_field,
                strict=True,
            )
        # Make sure the new FK constraint is present
        constraints = connection.introspection.get_constraints(connection.cursor(), Book._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["author_id"] and details['foreign_key']:
                self.assertEqual(details['foreign_key'], ('schema_tag', 'id'))
                break
        else:
            self.fail("No FK constraint for author_id found")

    def test_add_field(self):
        """
        Tests adding fields to models
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure there's no age field
        columns = self.column_classes(Author)
        self.assertNotIn("age", columns)
        # Alter the name field to a TextField
        new_field = IntegerField(null=True)
        new_field.set_attributes_from_name("age")
        with connection.schema_editor() as editor:
            editor.add_field(
                Author,
                new_field,
            )
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['age'][0], "IntegerField")
        self.assertEqual(columns['age'][1][6], True)

    def test_alter(self):
        """
        Tests simple altering of fields
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure the field is right to begin with
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        self.assertEqual(bool(columns['name'][1][6]), bool(connection.features.interprets_empty_strings_as_nulls))
        # Alter the name field to a TextField
        new_field = TextField(null=True)
        new_field.set_attributes_from_name("name")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Author,
                Author._meta.get_field_by_name("name")[0],
                new_field,
                strict=True,
            )
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "TextField")
        self.assertEqual(columns['name'][1][6], True)
        # Change nullability again
        new_field2 = TextField(null=False)
        new_field2.set_attributes_from_name("name")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Author,
                new_field,
                new_field2,
                strict=True,
            )
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "TextField")
        self.assertEqual(bool(columns['name'][1][6]), False)

    def test_rename(self):
        """
        Tests simple altering of fields
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure the field is right to begin with
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        self.assertNotIn("display_name", columns)
        # Alter the name field's name
        new_field = CharField(max_length=254)
        new_field.set_attributes_from_name("display_name")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Author,
                Author._meta.get_field_by_name("name")[0],
                new_field,
                strict = True,
            )
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['display_name'][0], "CharField")
        self.assertNotIn("name", columns)

    def test_m2m_create(self):
        """
        Tests M2M fields on models during creation
        """
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(TagM2MTest)
            editor.create_model(BookWithM2M)
        # Ensure there is now an m2m table there
        columns = self.column_classes(BookWithM2M._meta.get_field_by_name("tags")[0].rel.through)
        self.assertEqual(columns['tagm2mtest_id'][0], "IntegerField")

    def test_m2m(self):
        """
        Tests adding/removing M2M fields on models
        """
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithM2M)
            editor.create_model(TagM2MTest)
        # Create an M2M field
        new_field = ManyToManyField("schema.TagM2MTest", related_name="authors")
        new_field.contribute_to_class(AuthorWithM2M, "tags")
        try:
            # Ensure there's no m2m table there
            self.assertRaises(DatabaseError, self.column_classes, new_field.rel.through)
            # Add the field
            with connection.schema_editor() as editor:
                editor.add_field(
                    Author,
                    new_field,
                )
            # Ensure there is now an m2m table there
            columns = self.column_classes(new_field.rel.through)
            self.assertEqual(columns['tagm2mtest_id'][0], "IntegerField")
            # Remove the M2M table again
            with connection.schema_editor() as editor:
                editor.remove_field(
                    Author,
                    new_field,
                )
            # Ensure there's no m2m table there
            self.assertRaises(DatabaseError, self.column_classes, new_field.rel.through)
        finally:
            # Cleanup model states
            AuthorWithM2M._meta.local_many_to_many.remove(new_field)

    def test_m2m_repoint(self):
        """
        Tests repointing M2M fields
        """
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(BookWithM2M)
            editor.create_model(TagM2MTest)
            editor.create_model(UniqueTest)
        # Ensure the M2M exists and points to TagM2MTest
        constraints = connection.introspection.get_constraints(connection.cursor(), BookWithM2M._meta.get_field_by_name("tags")[0].rel.through._meta.db_table)
        if connection.features.supports_foreign_keys:
            for name, details in constraints.items():
                if details['columns'] == ["tagm2mtest_id"] and details['foreign_key']:
                    self.assertEqual(details['foreign_key'], ('schema_tagm2mtest', 'id'))
                    break
            else:
                self.fail("No FK constraint for tagm2mtest_id found")
        # Repoint the M2M
        new_field = ManyToManyField(UniqueTest)
        new_field.contribute_to_class(BookWithM2M, "uniques")
        try:
            with connection.schema_editor() as editor:
                editor.alter_field(
                    Author,
                    BookWithM2M._meta.get_field_by_name("tags")[0],
                    new_field,
                )
            # Ensure old M2M is gone
            self.assertRaises(DatabaseError, self.column_classes, BookWithM2M._meta.get_field_by_name("tags")[0].rel.through)
            # Ensure the new M2M exists and points to UniqueTest
            constraints = connection.introspection.get_constraints(connection.cursor(), new_field.rel.through._meta.db_table)
            if connection.features.supports_foreign_keys:
                for name, details in constraints.items():
                    if details['columns'] == ["uniquetest_id"] and details['foreign_key']:
                        self.assertEqual(details['foreign_key'], ('schema_uniquetest', 'id'))
                        break
                else:
                    self.fail("No FK constraint for uniquetest_id found")
        finally:
            # Cleanup model states
            BookWithM2M._meta.local_many_to_many.remove(new_field)
            del BookWithM2M._meta._m2m_cache

    @unittest.skipUnless(connection.features.supports_check_constraints, "No check constraints")
    def test_check_constraints(self):
        """
        Tests creating/deleting CHECK constraints
        """
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure the constraint exists
        constraints = connection.introspection.get_constraints(connection.cursor(), Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["height"] and details['check']:
                break
        else:
            self.fail("No check constraint for height found")
        # Alter the column to remove it
        new_field = IntegerField(null=True, blank=True)
        new_field.set_attributes_from_name("height")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Author,
                Author._meta.get_field_by_name("height")[0],
                new_field,
                strict = True,
            )
        constraints = connection.introspection.get_constraints(connection.cursor(), Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["height"] and details['check']:
                self.fail("Check constraint for height found")
        # Alter the column to re-add it
        with connection.schema_editor() as editor:
            editor.alter_field(
                Author,
                new_field,
                Author._meta.get_field_by_name("height")[0],
                strict = True,
            )
        constraints = connection.introspection.get_constraints(connection.cursor(), Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["height"] and details['check']:
                break
        else:
            self.fail("No check constraint for height found")

    def test_unique(self):
        """
        Tests removing and adding unique constraints to a single column.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
        # Ensure the field is unique to begin with
        Tag.objects.create(title="foo", slug="foo")
        self.assertRaises(IntegrityError, Tag.objects.create, title="bar", slug="foo")
        Tag.objects.all().delete()
        # Alter the slug field to be non-unique
        new_field = SlugField(unique=False)
        new_field.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Tag,
                Tag._meta.get_field_by_name("slug")[0],
                new_field,
                strict = True,
            )
        # Ensure the field is no longer unique
        Tag.objects.create(title="foo", slug="foo")
        Tag.objects.create(title="bar", slug="foo")
        Tag.objects.all().delete()
        # Alter the slug field to be unique
        new_new_field = SlugField(unique=True)
        new_new_field.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Tag,
                new_field,
                new_new_field,
                strict = True,
            )
        # Ensure the field is unique again
        Tag.objects.create(title="foo", slug="foo")
        self.assertRaises(IntegrityError, Tag.objects.create, title="bar", slug="foo")
        Tag.objects.all().delete()
        # Rename the field
        new_field = SlugField(unique=False)
        new_field.set_attributes_from_name("slug2")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Tag,
                Tag._meta.get_field_by_name("slug")[0],
                TagUniqueRename._meta.get_field_by_name("slug2")[0],
                strict = True,
            )
        # Ensure the field is still unique
        TagUniqueRename.objects.create(title="foo", slug2="foo")
        self.assertRaises(IntegrityError, TagUniqueRename.objects.create, title="bar", slug2="foo")
        Tag.objects.all().delete()

    def test_unique_together(self):
        """
        Tests removing and adding unique_together constraints on a model.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(UniqueTest)
        # Ensure the fields are unique to begin with
        UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.create(year=2011, slug="foo")
        UniqueTest.objects.create(year=2011, slug="bar")
        self.assertRaises(IntegrityError, UniqueTest.objects.create, year=2012, slug="foo")
        UniqueTest.objects.all().delete()
        # Alter the model to it's non-unique-together companion
        with connection.schema_editor() as editor:
            editor.alter_unique_together(
                UniqueTest,
                UniqueTest._meta.unique_together,
                [],
            )
        # Ensure the fields are no longer unique
        UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.all().delete()
        # Alter it back
        new_new_field = SlugField(unique=True)
        new_new_field.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_unique_together(
                UniqueTest,
                [],
                UniqueTest._meta.unique_together,
            )
        # Ensure the fields are unique again
        UniqueTest.objects.create(year=2012, slug="foo")
        self.assertRaises(IntegrityError, UniqueTest.objects.create, year=2012, slug="foo")
        UniqueTest.objects.all().delete()

    def test_index_together(self):
        """
        Tests removing and adding index_together constraints on a model.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
        # Ensure there's no index on the year/slug columns first
        self.assertEqual(
            False,
            any(
                c["index"]
                for c in connection.introspection.get_constraints(connection.cursor(), "schema_tag").values()
                if c['columns'] == ["slug", "title"]
            ),
        )
        # Alter the model to add an index
        with connection.schema_editor() as editor:
            editor.alter_index_together(
                Tag,
                [],
                [("slug", "title")],
            )
        # Ensure there is now an index
        self.assertEqual(
            True,
            any(
                c["index"]
                for c in connection.introspection.get_constraints(connection.cursor(), "schema_tag").values()
                if c['columns'] == ["slug", "title"]
            ),
        )
        # Alter it back
        new_new_field = SlugField(unique=True)
        new_new_field.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_index_together(
                Tag,
                [("slug", "title")],
                [],
            )
        # Ensure there's no index
        self.assertEqual(
            False,
            any(
                c["index"]
                for c in connection.introspection.get_constraints(connection.cursor(), "schema_tag").values()
                if c['columns'] == ["slug", "title"]
            ),
        )

    def test_create_index_together(self):
        """
        Tests creating models with index_together already defined
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(TagIndexed)
        # Ensure there is an index
        self.assertEqual(
            True,
            any(
                c["index"]
                for c in connection.introspection.get_constraints(connection.cursor(), "schema_tagindexed").values()
                if c['columns'] == ["slug", "title"]
            ),
        )

    def test_db_table(self):
        """
        Tests renaming of the table
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure the table is there to begin with
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        # Alter the table
        with connection.schema_editor() as editor:
            editor.alter_db_table(
                Author,
                "schema_author",
                "schema_otherauthor",
            )
        # Ensure the table is there afterwards
        Author._meta.db_table = "schema_otherauthor"
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        # Alter the table again
        with connection.schema_editor() as editor:
            editor.alter_db_table(
                Author,
                "schema_otherauthor",
                "schema_author",
            )
        # Ensure the table is still there
        Author._meta.db_table = "schema_author"
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")

    def test_indexes(self):
        """
        Tests creation/altering of indexes
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        # Ensure the table is there and has the right index
        self.assertIn(
            "title",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Alter to remove the index
        new_field = CharField(max_length=100, db_index=False)
        new_field.set_attributes_from_name("title")
        with connection.schema_editor() as editor:
            editor.alter_field(
                Book,
                Book._meta.get_field_by_name("title")[0],
                new_field,
                strict = True,
            )
        # Ensure the table is there and has no index
        self.assertNotIn(
            "title",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Alter to re-add the index
        with connection.schema_editor() as editor:
            editor.alter_field(
                Book,
                new_field,
                Book._meta.get_field_by_name("title")[0],
                strict = True,
            )
        # Ensure the table is there and has the index again
        self.assertIn(
            "title",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Add a unique column, verify that creates an implicit index
        with connection.schema_editor() as editor:
            editor.add_field(
                Book,
                BookWithSlug._meta.get_field_by_name("slug")[0],
            )
        self.assertIn(
            "slug",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )
        # Remove the unique, check the index goes with it
        new_field2 = CharField(max_length=20, unique=False)
        new_field2.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_field(
                BookWithSlug,
                BookWithSlug._meta.get_field_by_name("slug")[0],
                new_field2,
                strict = True,
            )
        self.assertNotIn(
            "slug",
            connection.introspection.get_indexes(connection.cursor(), Book._meta.db_table),
        )

    def test_primary_key(self):
        """
        Tests altering of the primary key
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
        # Ensure the table is there and has the right PK
        self.assertTrue(
            connection.introspection.get_indexes(connection.cursor(), Tag._meta.db_table)['id']['primary_key'],
        )
        # Alter to change the PK
        new_field = SlugField(primary_key=True)
        new_field.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.remove_field(Tag, Tag._meta.get_field_by_name("id")[0])
            editor.alter_field(
                Tag,
                Tag._meta.get_field_by_name("slug")[0],
                new_field,
            )
        # Ensure the PK changed
        self.assertNotIn(
            'id',
            connection.introspection.get_indexes(connection.cursor(), Tag._meta.db_table),
        )
        self.assertTrue(
            connection.introspection.get_indexes(connection.cursor(), Tag._meta.db_table)['slug']['primary_key'],
        )

    def test_context_manager_exit(self):
        """
        Ensures transaction is correctly closed when an error occurs
        inside a SchemaEditor context.
        """
        class SomeError(Exception):
            pass
        try:
            with connection.schema_editor() as editor:
                raise SomeError
        except SomeError:
            self.assertFalse(connection.in_atomic_block)
