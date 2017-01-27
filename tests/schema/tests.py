import datetime
import itertools
import unittest
from copy import copy
from unittest import mock

from django.db import (
    DatabaseError, IntegrityError, OperationalError, connection,
)
from django.db.models import Model
from django.db.models.deletion import CASCADE, PROTECT
from django.db.models.fields import (
    AutoField, BigIntegerField, BinaryField, BooleanField, CharField,
    DateField, DateTimeField, IntegerField, PositiveIntegerField, SlugField,
    TextField, TimeField,
)
from django.db.models.fields.related import (
    ForeignKey, ForeignObject, ManyToManyField, OneToOneField,
)
from django.db.models.indexes import Index
from django.db.transaction import TransactionManagementError, atomic
from django.test import (
    TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature,
)
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from .fields import (
    CustomManyToManyField, InheritedManyToManyField, MediumBlobField,
)
from .models import (
    Author, AuthorWithDefaultHeight, AuthorWithEvenLongerName, Book,
    BookForeignObj, BookWeak, BookWithLongName, BookWithO2O, BookWithoutAuthor,
    BookWithSlug, IntegerPK, Node, Note, NoteRename, Tag, TagIndexed,
    TagM2MTest, TagUniqueRename, Thing, UniqueTest, new_apps,
)


class SchemaTests(TransactionTestCase):
    """
    Tests for the schema-alteration code.

    Be aware that these tests are more liable than most to false results,
    as sometimes the code to check if a test has worked is almost as complex
    as the code it is testing.
    """

    available_apps = []

    models = [
        Author, AuthorWithDefaultHeight, AuthorWithEvenLongerName, Book,
        BookWeak, BookWithLongName, BookWithO2O, BookWithSlug, IntegerPK, Node,
        Note, Tag, TagIndexed, TagM2MTest, TagUniqueRename, Thing, UniqueTest,
    ]

    # Utility functions

    def setUp(self):
        # local_models should contain test dependent model classes that will be
        # automatically removed from the app cache on test tear down.
        self.local_models = []

    def tearDown(self):
        # Delete any tables made for our models
        self.delete_tables()
        new_apps.clear_cache()
        for model in new_apps.get_models():
            model._meta._expire_cache()
        if 'schema' in new_apps.all_models:
            for model in self.local_models:
                for many_to_many in model._meta.many_to_many:
                    through = many_to_many.remote_field.through
                    if through and through._meta.auto_created:
                        del new_apps.all_models['schema'][through._meta.model_name]
                del new_apps.all_models['schema'][model._meta.model_name]

    def delete_tables(self):
        "Deletes all model tables for our models for a clean test environment"
        converter = connection.introspection.table_name_converter
        with connection.schema_editor() as editor:
            connection.disable_constraint_checking()
            table_names = connection.introspection.table_names()
            for model in itertools.chain(SchemaTests.models, self.local_models):
                tbl = converter(model._meta.db_table)
                if tbl in table_names:
                    editor.delete_model(model)
                    table_names.remove(tbl)
            connection.enable_constraint_checking()

    def column_classes(self, model):
        with connection.cursor() as cursor:
            columns = {
                d[0]: (connection.introspection.get_field_type(d[1], d), d)
                for d in connection.introspection.get_table_description(
                    cursor,
                    model._meta.db_table,
                )
            }
        # SQLite has a different format for field_type
        for name, (type, desc) in columns.items():
            if isinstance(type, tuple):
                columns[name] = (type[0], desc)
        # SQLite also doesn't error properly
        if not columns:
            raise DatabaseError("Table does not exist (empty pragma)")
        return columns

    def get_primary_key(self, table):
        with connection.cursor() as cursor:
            return connection.introspection.get_primary_key_column(cursor, table)

    def get_indexes(self, table):
        """
        Get the indexes on the table using a new cursor.
        """
        with connection.cursor() as cursor:
            return [
                c['columns'][0]
                for c in connection.introspection.get_constraints(cursor, table).values()
                if c['index'] and len(c['columns']) == 1
            ]

    def get_constraints(self, table):
        """
        Get the constraints on a table using a new cursor.
        """
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def get_constraints_for_column(self, model, column_name):
        constraints = self.get_constraints(model._meta.db_table)
        constraints_for_column = []
        for name, details in constraints.items():
            if details['columns'] == [column_name]:
                constraints_for_column.append(name)
        return sorted(constraints_for_column)

    def check_added_field_default(self, schema_editor, model, field, field_name, expected_default,
                                  cast_function=None):
        with connection.cursor() as cursor:
            schema_editor.add_field(model, field)
            cursor.execute("SELECT {} FROM {};".format(field_name, model._meta.db_table))
            database_default = cursor.fetchall()[0][0]
            if cast_function and not type(database_default) == type(expected_default):
                database_default = cast_function(database_default)
            self.assertEqual(database_default, expected_default)

    def get_constraints_count(self, table, column, fk_to):
        """
        Return a dict with keys 'fks', 'uniques, and 'indexes' indicating the
        number of foreign keys, unique constraints, and indexes on
        `table`.`column`. The `fk_to` argument is a 2-tuple specifying the
        expected foreign key relationship's (table, column).
        """
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, table)
        counts = {'fks': 0, 'uniques': 0, 'indexes': 0}
        for c in constraints.values():
            if c['columns'] == [column]:
                if c['foreign_key'] == fk_to:
                    counts['fks'] += 1
                if c['unique']:
                    counts['uniques'] += 1
                elif c['index']:
                    counts['indexes'] += 1
        return counts

    def assertIndexOrder(self, table, index, order):
        constraints = self.get_constraints(table)
        self.assertIn(index, constraints)
        index_orders = constraints[index]['orders']
        self.assertTrue(all([(val == expected) for val, expected in zip(index_orders, order)]))

    # Tests
    def test_creation_deletion(self):
        """
        Tries creating a model's table, and then deleting it.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # The table is there
        list(Author.objects.all())
        # Clean up that table
        with connection.schema_editor() as editor:
            editor.delete_model(Author)
        # The table is gone
        with self.assertRaises(DatabaseError):
            list(Author.objects.all())

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_fk(self):
        "Creating tables out of FK order, then repointing, works"
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Book)
            editor.create_model(Author)
            editor.create_model(Tag)
        # Initial tables are there
        list(Author.objects.all())
        list(Book.objects.all())
        # Make sure the FK constraint is present
        with self.assertRaises(IntegrityError):
            Book.objects.create(
                author_id=1,
                title="Much Ado About Foreign Keys",
                pub_date=datetime.datetime.now(),
            )
        # Repoint the FK constraint
        old_field = Book._meta.get_field("author")
        new_field = ForeignKey(Tag, CASCADE)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(Book, old_field, new_field, strict=True)
        # Make sure the new FK constraint is present
        constraints = self.get_constraints(Book._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["author_id"] and details['foreign_key']:
                self.assertEqual(details['foreign_key'], ('schema_tag', 'id'))
                break
        else:
            self.fail("No FK constraint for author_id found")

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_fk_to_proxy(self):
        "Creating a FK to a proxy model creates database constraints."
        class AuthorProxy(Author):
            class Meta:
                app_label = 'schema'
                apps = new_apps
                proxy = True

        class AuthorRef(Model):
            author = ForeignKey(AuthorProxy, on_delete=CASCADE)

            class Meta:
                app_label = 'schema'
                apps = new_apps

        self.local_models = [AuthorProxy, AuthorRef]

        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(AuthorRef)
        constraints = self.get_constraints(AuthorRef._meta.db_table)
        for details in constraints.values():
            if details['columns'] == ['author_id'] and details['foreign_key']:
                self.assertEqual(details['foreign_key'], ('schema_author', 'id'))
                break
        else:
            self.fail('No FK constraint for author_id found')

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_fk_db_constraint(self):
        "The db_constraint parameter is respected"
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
            editor.create_model(Author)
            editor.create_model(BookWeak)
        # Initial tables are there
        list(Author.objects.all())
        list(Tag.objects.all())
        list(BookWeak.objects.all())
        # BookWeak doesn't have an FK constraint
        constraints = self.get_constraints(BookWeak._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["author_id"] and details['foreign_key']:
                self.fail("FK constraint for author_id found")
        # Make a db_constraint=False FK
        new_field = ForeignKey(Tag, CASCADE, db_constraint=False)
        new_field.set_attributes_from_name("tag")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        # No FK constraint is present
        constraints = self.get_constraints(Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["tag_id"] and details['foreign_key']:
                self.fail("FK constraint for tag_id found")
        # Alter to one with a constraint
        new_field2 = ForeignKey(Tag, CASCADE)
        new_field2.set_attributes_from_name("tag")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, new_field2, strict=True)
        # The new FK constraint is present
        constraints = self.get_constraints(Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["tag_id"] and details['foreign_key']:
                self.assertEqual(details['foreign_key'], ('schema_tag', 'id'))
                break
        else:
            self.fail("No FK constraint for tag_id found")
        # Alter to one without a constraint again
        new_field2 = ForeignKey(Tag, CASCADE)
        new_field2.set_attributes_from_name("tag")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field2, new_field, strict=True)
        # No FK constraint is present
        constraints = self.get_constraints(Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["tag_id"] and details['foreign_key']:
                self.fail("FK constraint for tag_id found")

    def _test_m2m_db_constraint(self, M2MFieldClass):
        class LocalAuthorWithM2M(Model):
            name = CharField(max_length=255)

            class Meta:
                app_label = 'schema'
                apps = new_apps

        self.local_models = [LocalAuthorWithM2M]

        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
            editor.create_model(LocalAuthorWithM2M)
        # Initial tables are there
        list(LocalAuthorWithM2M.objects.all())
        list(Tag.objects.all())
        # Make a db_constraint=False FK
        new_field = M2MFieldClass(Tag, related_name="authors", db_constraint=False)
        new_field.contribute_to_class(LocalAuthorWithM2M, "tags")
        # Add the field
        with connection.schema_editor() as editor:
            editor.add_field(LocalAuthorWithM2M, new_field)
        # No FK constraint is present
        constraints = self.get_constraints(new_field.remote_field.through._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["tag_id"] and details['foreign_key']:
                self.fail("FK constraint for tag_id found")

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_m2m_db_constraint(self):
        self._test_m2m_db_constraint(ManyToManyField)

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_m2m_db_constraint_custom(self):
        self._test_m2m_db_constraint(CustomManyToManyField)

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_m2m_db_constraint_inherited(self):
        self._test_m2m_db_constraint(InheritedManyToManyField)

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
        # Add the new field
        new_field = IntegerField(null=True)
        new_field.set_attributes_from_name("age")
        with CaptureQueriesContext(connection) as ctx, connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        drop_default_sql = editor.sql_alter_column_no_default % {
            'column': editor.quote_name(new_field.name),
        }
        self.assertFalse(any(drop_default_sql in query['sql'] for query in ctx.captured_queries))
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['age'][0], "IntegerField")
        self.assertEqual(columns['age'][1][6], True)

    def test_add_field_temp_default(self):
        """
        Tests adding fields to models with a temporary default
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure there's no age field
        columns = self.column_classes(Author)
        self.assertNotIn("age", columns)
        # Add some rows of data
        Author.objects.create(name="Andrew", height=30)
        Author.objects.create(name="Andrea")
        # Add a not-null field
        new_field = CharField(max_length=30, default="Godwin")
        new_field.set_attributes_from_name("surname")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['surname'][0], "CharField")
        self.assertEqual(columns['surname'][1][6],
                         connection.features.interprets_empty_strings_as_nulls)

    def test_add_field_temp_default_boolean(self):
        """
        Tests adding fields to models with a temporary default where
        the default is False. (#21783)
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure there's no age field
        columns = self.column_classes(Author)
        self.assertNotIn("age", columns)
        # Add some rows of data
        Author.objects.create(name="Andrew", height=30)
        Author.objects.create(name="Andrea")
        # Add a not-null field
        new_field = BooleanField(default=False)
        new_field.set_attributes_from_name("awesome")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        # BooleanField are stored as TINYINT(1) on MySQL.
        field_type = columns['awesome'][0]
        self.assertEqual(
            field_type,
            connection.features.introspected_boolean_field_type(new_field)
        )

    def test_add_field_default_transform(self):
        """
        Tests adding fields to models with a default that is not directly
        valid in the database (#22581)
        """

        class TestTransformField(IntegerField):

            # Weird field that saves the count of items in its value
            def get_default(self):
                return self.default

            def get_prep_value(self, value):
                if value is None:
                    return 0
                return len(value)

        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Add some rows of data
        Author.objects.create(name="Andrew", height=30)
        Author.objects.create(name="Andrea")
        # Add the field with a default it needs to cast (to string in this case)
        new_field = TestTransformField(default={1: 2})
        new_field.set_attributes_from_name("thing")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        # Ensure the field is there
        columns = self.column_classes(Author)
        field_type, field_info = columns['thing']
        self.assertEqual(field_type, 'IntegerField')
        # Make sure the values were transformed correctly
        self.assertEqual(Author.objects.extra(where=["thing = 1"]).count(), 2)

    def test_add_field_binary(self):
        """
        Tests binary fields get a sane default (#22851)
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Add the new field
        new_field = BinaryField(blank=True)
        new_field.set_attributes_from_name("bits")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        # MySQL annoyingly uses the same backend, so it'll come back as one of
        # these two types.
        self.assertIn(columns['bits'][0], ("BinaryField", "TextField"))

    @unittest.skipUnless(connection.vendor == 'mysql', "MySQL specific")
    def test_add_binaryfield_mediumblob(self):
        """
        Test adding a custom-sized binary field on MySQL (#24846).
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Add the new field with default
        new_field = MediumBlobField(blank=True, default=b'123')
        new_field.set_attributes_from_name('bits')
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        columns = self.column_classes(Author)
        # Introspection treats BLOBs as TextFields
        self.assertEqual(columns['bits'][0], "TextField")

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
        old_field = Author._meta.get_field("name")
        new_field = TextField(null=True)
        new_field.set_attributes_from_name("name")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "TextField")
        self.assertEqual(columns['name'][1][6], True)
        # Change nullability again
        new_field2 = TextField(null=False)
        new_field2.set_attributes_from_name("name")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, new_field2, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "TextField")
        self.assertEqual(bool(columns['name'][1][6]), bool(connection.features.interprets_empty_strings_as_nulls))

    def test_alter_text_field(self):
        # Regression for "BLOB/TEXT column 'info' can't have a default value")
        # on MySQL.
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        old_field = Note._meta.get_field("info")
        new_field = TextField(blank=True)
        new_field.set_attributes_from_name("info")
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)

    @skipUnlessDBFeature('can_defer_constraint_checks', 'can_rollback_ddl')
    def test_alter_fk_checks_deferred_constraints(self):
        """
        #25492 - Altering a foreign key's structure and data in the same
        transaction.
        """
        with connection.schema_editor() as editor:
            editor.create_model(Node)
        old_field = Node._meta.get_field('parent')
        new_field = ForeignKey(Node, CASCADE)
        new_field.set_attributes_from_name('parent')
        parent = Node.objects.create()
        with connection.schema_editor() as editor:
            # Update the parent FK to create a deferred constraint check.
            Node.objects.update(parent=parent)
            editor.alter_field(Node, old_field, new_field, strict=True)

    def test_alter_text_field_to_date_field(self):
        """
        #25002 - Test conversion of text field to date field.
        """
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        Note.objects.create(info='1988-05-05')
        old_field = Note._meta.get_field('info')
        new_field = DateField(blank=True)
        new_field.set_attributes_from_name('info')
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)
        # Make sure the field isn't nullable
        columns = self.column_classes(Note)
        self.assertFalse(columns['info'][1][6])

    def test_alter_text_field_to_datetime_field(self):
        """
        #25002 - Test conversion of text field to datetime field.
        """
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        Note.objects.create(info='1988-05-05 3:16:17.4567')
        old_field = Note._meta.get_field('info')
        new_field = DateTimeField(blank=True)
        new_field.set_attributes_from_name('info')
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)
        # Make sure the field isn't nullable
        columns = self.column_classes(Note)
        self.assertFalse(columns['info'][1][6])

    def test_alter_text_field_to_time_field(self):
        """
        #25002 - Test conversion of text field to time field.
        """
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        Note.objects.create(info='3:16:17.4567')
        old_field = Note._meta.get_field('info')
        new_field = TimeField(blank=True)
        new_field.set_attributes_from_name('info')
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)
        # Make sure the field isn't nullable
        columns = self.column_classes(Note)
        self.assertFalse(columns['info'][1][6])

    @skipIfDBFeature('interprets_empty_strings_as_nulls')
    def test_alter_textual_field_keep_null_status(self):
        """
        Changing a field type shouldn't affect the not null status.
        """
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        with self.assertRaises(IntegrityError):
            Note.objects.create(info=None)
        old_field = Note._meta.get_field("info")
        new_field = CharField(max_length=50)
        new_field.set_attributes_from_name("info")
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)
        with self.assertRaises(IntegrityError):
            Note.objects.create(info=None)

    def test_alter_numeric_field_keep_null_status(self):
        """
        Changing a field type shouldn't affect the not null status.
        """
        with connection.schema_editor() as editor:
            editor.create_model(UniqueTest)
        with self.assertRaises(IntegrityError):
            UniqueTest.objects.create(year=None, slug='aaa')
        old_field = UniqueTest._meta.get_field("year")
        new_field = BigIntegerField()
        new_field.set_attributes_from_name("year")
        with connection.schema_editor() as editor:
            editor.alter_field(UniqueTest, old_field, new_field, strict=True)
        with self.assertRaises(IntegrityError):
            UniqueTest.objects.create(year=None, slug='bbb')

    def test_alter_null_to_not_null(self):
        """
        #23609 - Tests handling of default values when altering from NULL to NOT NULL.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure the field is right to begin with
        columns = self.column_classes(Author)
        self.assertTrue(columns['height'][1][6])
        # Create some test data
        Author.objects.create(name='Not null author', height=12)
        Author.objects.create(name='Null author')
        # Verify null value
        self.assertEqual(Author.objects.get(name='Not null author').height, 12)
        self.assertIsNone(Author.objects.get(name='Null author').height)
        # Alter the height field to NOT NULL with default
        old_field = Author._meta.get_field("height")
        new_field = PositiveIntegerField(default=42)
        new_field.set_attributes_from_name("height")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertFalse(columns['height'][1][6])
        # Verify default value
        self.assertEqual(Author.objects.get(name='Not null author').height, 12)
        self.assertEqual(Author.objects.get(name='Null author').height, 42)

    def test_alter_charfield_to_null(self):
        """
        #24307 - Should skip an alter statement on databases with
        interprets_empty_strings_as_null when changing a CharField to null.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Change the CharField to null
        old_field = Author._meta.get_field('name')
        new_field = copy(old_field)
        new_field.null = True
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)

    def test_alter_textfield_to_null(self):
        """
        #24307 - Should skip an alter statement on databases with
        interprets_empty_strings_as_null when changing a TextField to null.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        # Change the TextField to null
        old_field = Note._meta.get_field('info')
        new_field = copy(old_field)
        new_field.null = True
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)

    @skipUnlessDBFeature('supports_combined_alters')
    def test_alter_null_to_not_null_keeping_default(self):
        """
        #23738 - Can change a nullable field with default to non-nullable
        with the same default.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithDefaultHeight)
        # Ensure the field is right to begin with
        columns = self.column_classes(AuthorWithDefaultHeight)
        self.assertTrue(columns['height'][1][6])
        # Alter the height field to NOT NULL keeping the previous default
        old_field = AuthorWithDefaultHeight._meta.get_field("height")
        new_field = PositiveIntegerField(default=42)
        new_field.set_attributes_from_name("height")
        with connection.schema_editor() as editor:
            editor.alter_field(AuthorWithDefaultHeight, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(AuthorWithDefaultHeight)
        self.assertFalse(columns['height'][1][6])

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_alter_fk(self):
        """
        Tests altering of FKs
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        # Ensure the field is right to begin with
        columns = self.column_classes(Book)
        self.assertEqual(columns['author_id'][0], "IntegerField")
        # Make sure the FK constraint is present
        constraints = self.get_constraints(Book._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["author_id"] and details['foreign_key']:
                self.assertEqual(details['foreign_key'], ('schema_author', 'id'))
                break
        else:
            self.fail("No FK constraint for author_id found")
        # Alter the FK
        old_field = Book._meta.get_field("author")
        new_field = ForeignKey(Author, CASCADE, editable=False)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(Book, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(Book)
        self.assertEqual(columns['author_id'][0], "IntegerField")
        # Make sure the FK constraint is present
        constraints = self.get_constraints(Book._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["author_id"] and details['foreign_key']:
                self.assertEqual(details['foreign_key'], ('schema_author', 'id'))
                break
        else:
            self.fail("No FK constraint for author_id found")

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_alter_to_fk(self):
        """
        #24447 - Tests adding a FK constraint for an existing column
        """
        class LocalBook(Model):
            author = IntegerField()
            title = CharField(max_length=100, db_index=True)
            pub_date = DateTimeField()

            class Meta:
                app_label = 'schema'
                apps = new_apps

        self.local_models = [LocalBook]

        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(LocalBook)
        # Ensure no FK constraint exists
        constraints = self.get_constraints(LocalBook._meta.db_table)
        for name, details in constraints.items():
            if details['foreign_key']:
                self.fail('Found an unexpected FK constraint to %s' % details['columns'])
        old_field = LocalBook._meta.get_field("author")
        new_field = ForeignKey(Author, CASCADE)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(LocalBook, old_field, new_field, strict=True)
        constraints = self.get_constraints(LocalBook._meta.db_table)
        # Ensure FK constraint exists
        for name, details in constraints.items():
            if details['foreign_key'] and details['columns'] == ["author_id"]:
                self.assertEqual(details['foreign_key'], ('schema_author', 'id'))
                break
        else:
            self.fail("No FK constraint for author_id found")

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_alter_o2o_to_fk(self):
        """
        #24163 - Tests altering of OneToOneField to ForeignKey
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(BookWithO2O)
        # Ensure the field is right to begin with
        columns = self.column_classes(BookWithO2O)
        self.assertEqual(columns['author_id'][0], "IntegerField")
        # Ensure the field is unique
        author = Author.objects.create(name="Joe")
        BookWithO2O.objects.create(author=author, title="Django 1", pub_date=datetime.datetime.now())
        with self.assertRaises(IntegrityError):
            BookWithO2O.objects.create(author=author, title="Django 2", pub_date=datetime.datetime.now())
        BookWithO2O.objects.all().delete()
        # Make sure the FK constraint is present
        constraints = self.get_constraints(BookWithO2O._meta.db_table)
        author_is_fk = False
        for name, details in constraints.items():
            if details['columns'] == ['author_id']:
                if details['foreign_key'] and details['foreign_key'] == ('schema_author', 'id'):
                    author_is_fk = True
        self.assertTrue(author_is_fk, "No FK constraint for author_id found")
        # Alter the OneToOneField to ForeignKey
        old_field = BookWithO2O._meta.get_field("author")
        new_field = ForeignKey(Author, CASCADE)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithO2O, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(Book)
        self.assertEqual(columns['author_id'][0], "IntegerField")
        # Ensure the field is not unique anymore
        Book.objects.create(author=author, title="Django 1", pub_date=datetime.datetime.now())
        Book.objects.create(author=author, title="Django 2", pub_date=datetime.datetime.now())
        # Make sure the FK constraint is still present
        constraints = self.get_constraints(Book._meta.db_table)
        author_is_fk = False
        for name, details in constraints.items():
            if details['columns'] == ['author_id']:
                if details['foreign_key'] and details['foreign_key'] == ('schema_author', 'id'):
                    author_is_fk = True
        self.assertTrue(author_is_fk, "No FK constraint for author_id found")

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_alter_fk_to_o2o(self):
        """
        #24163 - Tests altering of ForeignKey to OneToOneField
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        # Ensure the field is right to begin with
        columns = self.column_classes(Book)
        self.assertEqual(columns['author_id'][0], "IntegerField")
        # Ensure the field is not unique
        author = Author.objects.create(name="Joe")
        Book.objects.create(author=author, title="Django 1", pub_date=datetime.datetime.now())
        Book.objects.create(author=author, title="Django 2", pub_date=datetime.datetime.now())
        Book.objects.all().delete()
        # Make sure the FK constraint is present
        constraints = self.get_constraints(Book._meta.db_table)
        author_is_fk = False
        for name, details in constraints.items():
            if details['columns'] == ['author_id']:
                if details['foreign_key'] and details['foreign_key'] == ('schema_author', 'id'):
                    author_is_fk = True
        self.assertTrue(author_is_fk, "No FK constraint for author_id found")
        # Alter the ForeignKey to OneToOneField
        old_field = Book._meta.get_field("author")
        new_field = OneToOneField(Author, CASCADE)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(Book, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(BookWithO2O)
        self.assertEqual(columns['author_id'][0], "IntegerField")
        # Ensure the field is unique now
        BookWithO2O.objects.create(author=author, title="Django 1", pub_date=datetime.datetime.now())
        with self.assertRaises(IntegrityError):
            BookWithO2O.objects.create(author=author, title="Django 2", pub_date=datetime.datetime.now())
        # Make sure the FK constraint is present
        constraints = self.get_constraints(BookWithO2O._meta.db_table)
        author_is_fk = False
        for name, details in constraints.items():
            if details['columns'] == ['author_id']:
                if details['foreign_key'] and details['foreign_key'] == ('schema_author', 'id'):
                    author_is_fk = True
        self.assertTrue(author_is_fk, "No FK constraint for author_id found")

    def test_alter_field_fk_to_o2o(self):
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        expected_fks = 1 if connection.features.supports_foreign_keys else 0

        # Check the index is right to begin with.
        counts = self.get_constraints_count(
            Book._meta.db_table,
            Book._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 0, 'indexes': 1})

        old_field = Book._meta.get_field('author')
        new_field = OneToOneField(Author, CASCADE)
        new_field.set_attributes_from_name('author')
        with connection.schema_editor() as editor:
            editor.alter_field(Book, old_field, new_field, strict=True)

        counts = self.get_constraints_count(
            Book._meta.db_table,
            Book._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        # The index on ForeignKey is replaced with a unique constraint for OneToOneField.
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 1, 'indexes': 0})

    def test_alter_field_fk_keeps_index(self):
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        expected_fks = 1 if connection.features.supports_foreign_keys else 0

        # Check the index is right to begin with.
        counts = self.get_constraints_count(
            Book._meta.db_table,
            Book._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 0, 'indexes': 1})

        old_field = Book._meta.get_field('author')
        # on_delete changed from CASCADE.
        new_field = ForeignKey(Author, PROTECT)
        new_field.set_attributes_from_name('author')
        with connection.schema_editor() as editor:
            editor.alter_field(Book, old_field, new_field, strict=True)

        counts = self.get_constraints_count(
            Book._meta.db_table,
            Book._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        # The index remains.
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 0, 'indexes': 1})

    def test_alter_field_o2o_to_fk(self):
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(BookWithO2O)
        expected_fks = 1 if connection.features.supports_foreign_keys else 0

        # Check the unique constraint is right to begin with.
        counts = self.get_constraints_count(
            BookWithO2O._meta.db_table,
            BookWithO2O._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 1, 'indexes': 0})

        old_field = BookWithO2O._meta.get_field('author')
        new_field = ForeignKey(Author, CASCADE)
        new_field.set_attributes_from_name('author')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithO2O, old_field, new_field, strict=True)

        counts = self.get_constraints_count(
            BookWithO2O._meta.db_table,
            BookWithO2O._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        # The unique constraint on OneToOneField is replaced with an index for ForeignKey.
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 0, 'indexes': 1})

    def test_alter_field_o2o_keeps_unique(self):
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(BookWithO2O)
        expected_fks = 1 if connection.features.supports_foreign_keys else 0

        # Check the unique constraint is right to begin with.
        counts = self.get_constraints_count(
            BookWithO2O._meta.db_table,
            BookWithO2O._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 1, 'indexes': 0})

        old_field = BookWithO2O._meta.get_field('author')
        # on_delete changed from CASCADE.
        new_field = OneToOneField(Author, PROTECT)
        new_field.set_attributes_from_name('author')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithO2O, old_field, new_field, strict=True)

        counts = self.get_constraints_count(
            BookWithO2O._meta.db_table,
            BookWithO2O._meta.get_field('author').column,
            (Author._meta.db_table, Author._meta.pk.column),
        )
        # The unique constraint remains.
        self.assertEqual(counts, {'fks': expected_fks, 'uniques': 1, 'indexes': 0})

    def test_alter_db_table_case(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Alter the case of the table
        old_table_name = Author._meta.db_table
        with connection.schema_editor() as editor:
            editor.alter_db_table(Author, old_table_name, old_table_name.upper())

    def test_alter_implicit_id_to_explicit(self):
        """
        Should be able to convert an implicit "id" field to an explicit "id"
        primary key field.
        """
        with connection.schema_editor() as editor:
            editor.create_model(Author)

        old_field = Author._meta.get_field("id")
        new_field = AutoField(primary_key=True)
        new_field.set_attributes_from_name("id")
        new_field.model = Author
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        # This will fail if DROP DEFAULT is inadvertently executed on this
        # field which drops the id sequence, at least on PostgreSQL.
        Author.objects.create(name='Foo')
        Author.objects.create(name='Bar')

    def test_alter_int_pk_to_autofield_pk(self):
        """
        Should be able to rename an IntegerField(primary_key=True) to
        AutoField(primary_key=True).
        """
        with connection.schema_editor() as editor:
            editor.create_model(IntegerPK)

        old_field = IntegerPK._meta.get_field('i')
        new_field = AutoField(primary_key=True)
        new_field.model = IntegerPK
        new_field.set_attributes_from_name('i')

        with connection.schema_editor() as editor:
            editor.alter_field(IntegerPK, old_field, new_field, strict=True)

    def test_alter_int_pk_to_int_unique(self):
        """
        Should be able to rename an IntegerField(primary_key=True) to
        IntegerField(unique=True).
        """
        class IntegerUnique(Model):
            i = IntegerField(unique=True)
            j = IntegerField(primary_key=True)

            class Meta:
                app_label = 'schema'
                apps = new_apps
                db_table = 'INTEGERPK'

        with connection.schema_editor() as editor:
            editor.create_model(IntegerPK)

        # model requires a new PK
        old_field = IntegerPK._meta.get_field('j')
        new_field = IntegerField(primary_key=True)
        new_field.model = IntegerPK
        new_field.set_attributes_from_name('j')

        with connection.schema_editor() as editor:
            editor.alter_field(IntegerPK, old_field, new_field, strict=True)

        old_field = IntegerPK._meta.get_field('i')
        new_field = IntegerField(unique=True)
        new_field.model = IntegerPK
        new_field.set_attributes_from_name('i')

        with connection.schema_editor() as editor:
            editor.alter_field(IntegerPK, old_field, new_field, strict=True)

        # Ensure unique constraint works.
        IntegerUnique.objects.create(i=1, j=1)
        with self.assertRaises(IntegrityError):
            IntegerUnique.objects.create(i=1, j=2)

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
        old_field = Author._meta.get_field("name")
        new_field = CharField(max_length=254)
        new_field.set_attributes_from_name("display_name")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(Author)
        self.assertEqual(columns['display_name'][0], "CharField")
        self.assertNotIn("name", columns)

    @skipIfDBFeature('interprets_empty_strings_as_nulls')
    def test_rename_keep_null_status(self):
        """
        Renaming a field shouldn't affect the not null status.
        """
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        with self.assertRaises(IntegrityError):
            Note.objects.create(info=None)
        old_field = Note._meta.get_field("info")
        new_field = TextField()
        new_field.set_attributes_from_name("detail_info")
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)
        columns = self.column_classes(Note)
        self.assertEqual(columns['detail_info'][0], "TextField")
        self.assertNotIn("info", columns)
        with self.assertRaises(IntegrityError):
            NoteRename.objects.create(detail_info=None)

    def _test_m2m_create(self, M2MFieldClass):
        """
        Tests M2M fields on models during creation
        """
        class LocalBookWithM2M(Model):
            author = ForeignKey(Author, CASCADE)
            title = CharField(max_length=100, db_index=True)
            pub_date = DateTimeField()
            tags = M2MFieldClass("TagM2MTest", related_name="books")

            class Meta:
                app_label = 'schema'
                apps = new_apps
        self.local_models = [LocalBookWithM2M]
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(TagM2MTest)
            editor.create_model(LocalBookWithM2M)
        # Ensure there is now an m2m table there
        columns = self.column_classes(LocalBookWithM2M._meta.get_field("tags").remote_field.through)
        self.assertEqual(columns['tagm2mtest_id'][0], "IntegerField")

    def test_m2m_create(self):
        self._test_m2m_create(ManyToManyField)

    def test_m2m_create_custom(self):
        self._test_m2m_create(CustomManyToManyField)

    def test_m2m_create_inherited(self):
        self._test_m2m_create(InheritedManyToManyField)

    def _test_m2m_create_through(self, M2MFieldClass):
        """
        Tests M2M fields on models during creation with through models
        """
        class LocalTagThrough(Model):
            book = ForeignKey("schema.LocalBookWithM2MThrough", CASCADE)
            tag = ForeignKey("schema.TagM2MTest", CASCADE)

            class Meta:
                app_label = 'schema'
                apps = new_apps

        class LocalBookWithM2MThrough(Model):
            tags = M2MFieldClass("TagM2MTest", related_name="books", through=LocalTagThrough)

            class Meta:
                app_label = 'schema'
                apps = new_apps

        self.local_models = [LocalTagThrough, LocalBookWithM2MThrough]

        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(LocalTagThrough)
            editor.create_model(TagM2MTest)
            editor.create_model(LocalBookWithM2MThrough)
        # Ensure there is now an m2m table there
        columns = self.column_classes(LocalTagThrough)
        self.assertEqual(columns['book_id'][0], "IntegerField")
        self.assertEqual(columns['tag_id'][0], "IntegerField")

    def test_m2m_create_through(self):
        self._test_m2m_create_through(ManyToManyField)

    def test_m2m_create_through_custom(self):
        self._test_m2m_create_through(CustomManyToManyField)

    def test_m2m_create_through_inherited(self):
        self._test_m2m_create_through(InheritedManyToManyField)

    def _test_m2m(self, M2MFieldClass):
        """
        Tests adding/removing M2M fields on models
        """
        class LocalAuthorWithM2M(Model):
            name = CharField(max_length=255)

            class Meta:
                app_label = 'schema'
                apps = new_apps

        self.local_models = [LocalAuthorWithM2M]

        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(LocalAuthorWithM2M)
            editor.create_model(TagM2MTest)
        # Create an M2M field
        new_field = M2MFieldClass("schema.TagM2MTest", related_name="authors")
        new_field.contribute_to_class(LocalAuthorWithM2M, "tags")
        # Ensure there's no m2m table there
        with self.assertRaises(DatabaseError):
            self.column_classes(new_field.remote_field.through)
        # Add the field
        with connection.schema_editor() as editor:
            editor.add_field(LocalAuthorWithM2M, new_field)
        # Ensure there is now an m2m table there
        columns = self.column_classes(new_field.remote_field.through)
        self.assertEqual(columns['tagm2mtest_id'][0], "IntegerField")

        # "Alter" the field. This should not rename the DB table to itself.
        with connection.schema_editor() as editor:
            editor.alter_field(LocalAuthorWithM2M, new_field, new_field, strict=True)

        # Remove the M2M table again
        with connection.schema_editor() as editor:
            editor.remove_field(LocalAuthorWithM2M, new_field)
        # Ensure there's no m2m table there
        with self.assertRaises(DatabaseError):
            self.column_classes(new_field.remote_field.through)

        # Make sure the model state is coherent with the table one now that
        # we've removed the tags field.
        opts = LocalAuthorWithM2M._meta
        opts.local_many_to_many.remove(new_field)
        del new_apps.all_models['schema'][new_field.remote_field.through._meta.model_name]
        opts._expire_cache()

    def test_m2m(self):
        self._test_m2m(ManyToManyField)

    def test_m2m_custom(self):
        self._test_m2m(CustomManyToManyField)

    def test_m2m_inherited(self):
        self._test_m2m(InheritedManyToManyField)

    def _test_m2m_through_alter(self, M2MFieldClass):
        """
        Tests altering M2Ms with explicit through models (should no-op)
        """
        class LocalAuthorTag(Model):
            author = ForeignKey("schema.LocalAuthorWithM2MThrough", CASCADE)
            tag = ForeignKey("schema.TagM2MTest", CASCADE)

            class Meta:
                app_label = 'schema'
                apps = new_apps

        class LocalAuthorWithM2MThrough(Model):
            name = CharField(max_length=255)
            tags = M2MFieldClass("schema.TagM2MTest", related_name="authors", through=LocalAuthorTag)

            class Meta:
                app_label = 'schema'
                apps = new_apps

        self.local_models = [LocalAuthorTag, LocalAuthorWithM2MThrough]

        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(LocalAuthorTag)
            editor.create_model(LocalAuthorWithM2MThrough)
            editor.create_model(TagM2MTest)
        # Ensure the m2m table is there
        self.assertEqual(len(self.column_classes(LocalAuthorTag)), 3)
        # "Alter" the field's blankness. This should not actually do anything.
        old_field = LocalAuthorWithM2MThrough._meta.get_field("tags")
        new_field = M2MFieldClass("schema.TagM2MTest", related_name="authors", through=LocalAuthorTag)
        new_field.contribute_to_class(LocalAuthorWithM2MThrough, "tags")
        with connection.schema_editor() as editor:
            editor.alter_field(LocalAuthorWithM2MThrough, old_field, new_field, strict=True)
        # Ensure the m2m table is still there
        self.assertEqual(len(self.column_classes(LocalAuthorTag)), 3)

    def test_m2m_through_alter(self):
        self._test_m2m_through_alter(ManyToManyField)

    def test_m2m_through_alter_custom(self):
        self._test_m2m_through_alter(CustomManyToManyField)

    def test_m2m_through_alter_inherited(self):
        self._test_m2m_through_alter(InheritedManyToManyField)

    def _test_m2m_repoint(self, M2MFieldClass):
        """
        Tests repointing M2M fields
        """
        class LocalBookWithM2M(Model):
            author = ForeignKey(Author, CASCADE)
            title = CharField(max_length=100, db_index=True)
            pub_date = DateTimeField()
            tags = M2MFieldClass("TagM2MTest", related_name="books")

            class Meta:
                app_label = 'schema'
                apps = new_apps
        self.local_models = [LocalBookWithM2M]
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(LocalBookWithM2M)
            editor.create_model(TagM2MTest)
            editor.create_model(UniqueTest)
        # Ensure the M2M exists and points to TagM2MTest
        constraints = self.get_constraints(
            LocalBookWithM2M._meta.get_field("tags").remote_field.through._meta.db_table
        )
        if connection.features.supports_foreign_keys:
            for name, details in constraints.items():
                if details['columns'] == ["tagm2mtest_id"] and details['foreign_key']:
                    self.assertEqual(details['foreign_key'], ('schema_tagm2mtest', 'id'))
                    break
            else:
                self.fail("No FK constraint for tagm2mtest_id found")
        # Repoint the M2M
        old_field = LocalBookWithM2M._meta.get_field("tags")
        new_field = M2MFieldClass(UniqueTest)
        new_field.contribute_to_class(LocalBookWithM2M, "uniques")
        with connection.schema_editor() as editor:
            editor.alter_field(LocalBookWithM2M, old_field, new_field, strict=True)
        # Ensure old M2M is gone
        with self.assertRaises(DatabaseError):
            self.column_classes(LocalBookWithM2M._meta.get_field("tags").remote_field.through)

        # This model looks like the new model and is used for teardown.
        opts = LocalBookWithM2M._meta
        opts.local_many_to_many.remove(old_field)
        # Ensure the new M2M exists and points to UniqueTest
        constraints = self.get_constraints(new_field.remote_field.through._meta.db_table)
        if connection.features.supports_foreign_keys:
            for name, details in constraints.items():
                if details['columns'] == ["uniquetest_id"] and details['foreign_key']:
                    self.assertEqual(details['foreign_key'], ('schema_uniquetest', 'id'))
                    break
            else:
                self.fail("No FK constraint for uniquetest_id found")

    def test_m2m_repoint(self):
        self._test_m2m_repoint(ManyToManyField)

    def test_m2m_repoint_custom(self):
        self._test_m2m_repoint(CustomManyToManyField)

    def test_m2m_repoint_inherited(self):
        self._test_m2m_repoint(InheritedManyToManyField)

    @skipUnlessDBFeature('supports_column_check_constraints')
    def test_check_constraints(self):
        """
        Tests creating/deleting CHECK constraints
        """
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure the constraint exists
        constraints = self.get_constraints(Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["height"] and details['check']:
                break
        else:
            self.fail("No check constraint for height found")
        # Alter the column to remove it
        old_field = Author._meta.get_field("height")
        new_field = IntegerField(null=True, blank=True)
        new_field.set_attributes_from_name("height")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        constraints = self.get_constraints(Author._meta.db_table)
        for name, details in constraints.items():
            if details['columns'] == ["height"] and details['check']:
                self.fail("Check constraint for height found")
        # Alter the column to re-add it
        new_field2 = Author._meta.get_field("height")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, new_field2, strict=True)
        constraints = self.get_constraints(Author._meta.db_table)
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
        with self.assertRaises(IntegrityError):
            Tag.objects.create(title="bar", slug="foo")
        Tag.objects.all().delete()
        # Alter the slug field to be non-unique
        old_field = Tag._meta.get_field("slug")
        new_field = SlugField(unique=False)
        new_field.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_field(Tag, old_field, new_field, strict=True)
        # Ensure the field is no longer unique
        Tag.objects.create(title="foo", slug="foo")
        Tag.objects.create(title="bar", slug="foo")
        Tag.objects.all().delete()
        # Alter the slug field to be unique
        new_field2 = SlugField(unique=True)
        new_field2.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_field(Tag, new_field, new_field2, strict=True)
        # Ensure the field is unique again
        Tag.objects.create(title="foo", slug="foo")
        with self.assertRaises(IntegrityError):
            Tag.objects.create(title="bar", slug="foo")
        Tag.objects.all().delete()
        # Rename the field
        new_field3 = SlugField(unique=True)
        new_field3.set_attributes_from_name("slug2")
        with connection.schema_editor() as editor:
            editor.alter_field(Tag, new_field2, new_field3, strict=True)
        # Ensure the field is still unique
        TagUniqueRename.objects.create(title="foo", slug2="foo")
        with self.assertRaises(IntegrityError):
            TagUniqueRename.objects.create(title="bar", slug2="foo")
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
        with self.assertRaises(IntegrityError):
            UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.all().delete()
        # Alter the model to its non-unique-together companion
        with connection.schema_editor() as editor:
            editor.alter_unique_together(UniqueTest, UniqueTest._meta.unique_together, [])
        # Ensure the fields are no longer unique
        UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.all().delete()
        # Alter it back
        new_field2 = SlugField(unique=True)
        new_field2.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_unique_together(UniqueTest, [], UniqueTest._meta.unique_together)
        # Ensure the fields are unique again
        UniqueTest.objects.create(year=2012, slug="foo")
        with self.assertRaises(IntegrityError):
            UniqueTest.objects.create(year=2012, slug="foo")
        UniqueTest.objects.all().delete()

    def test_unique_together_with_fk(self):
        """
        Tests removing and adding unique_together constraints that include
        a foreign key.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        # Ensure the fields are unique to begin with
        self.assertEqual(Book._meta.unique_together, ())
        # Add the unique_together constraint
        with connection.schema_editor() as editor:
            editor.alter_unique_together(Book, [], [['author', 'title']])
        # Alter it back
        with connection.schema_editor() as editor:
            editor.alter_unique_together(Book, [['author', 'title']], [])

    def test_unique_together_with_fk_with_existing_index(self):
        """
        Tests removing and adding unique_together constraints that include
        a foreign key, where the foreign key is added after the model is
        created.
        """
        # Create the tables
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(BookWithoutAuthor)
            new_field = ForeignKey(Author, CASCADE)
            new_field.set_attributes_from_name('author')
            editor.add_field(BookWithoutAuthor, new_field)
        # Ensure the fields aren't unique to begin with
        self.assertEqual(Book._meta.unique_together, ())
        # Add the unique_together constraint
        with connection.schema_editor() as editor:
            editor.alter_unique_together(Book, [], [['author', 'title']])
        # Alter it back
        with connection.schema_editor() as editor:
            editor.alter_unique_together(Book, [['author', 'title']], [])

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
                for c in self.get_constraints("schema_tag").values()
                if c['columns'] == ["slug", "title"]
            ),
        )
        # Alter the model to add an index
        with connection.schema_editor() as editor:
            editor.alter_index_together(Tag, [], [("slug", "title")])
        # Ensure there is now an index
        self.assertEqual(
            True,
            any(
                c["index"]
                for c in self.get_constraints("schema_tag").values()
                if c['columns'] == ["slug", "title"]
            ),
        )
        # Alter it back
        new_field2 = SlugField(unique=True)
        new_field2.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_index_together(Tag, [("slug", "title")], [])
        # Ensure there's no index
        self.assertEqual(
            False,
            any(
                c["index"]
                for c in self.get_constraints("schema_tag").values()
                if c['columns'] == ["slug", "title"]
            ),
        )

    def test_index_together_with_fk(self):
        """
        Tests removing and adding index_together constraints that include
        a foreign key.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        # Ensure the fields are unique to begin with
        self.assertEqual(Book._meta.index_together, ())
        # Add the unique_together constraint
        with connection.schema_editor() as editor:
            editor.alter_index_together(Book, [], [['author', 'title']])
        # Alter it back
        with connection.schema_editor() as editor:
            editor.alter_index_together(Book, [['author', 'title']], [])

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
                for c in self.get_constraints("schema_tagindexed").values()
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
            editor.alter_db_table(Author, "schema_author", "schema_otherauthor")
        # Ensure the table is there afterwards
        Author._meta.db_table = "schema_otherauthor"
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        # Alter the table again
        with connection.schema_editor() as editor:
            editor.alter_db_table(Author, "schema_otherauthor", "schema_author")
        # Ensure the table is still there
        Author._meta.db_table = "schema_author"
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")

    def test_add_remove_index(self):
        """
        Tests index addition and removal
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure the table is there and has no index
        self.assertNotIn('title', self.get_indexes(Author._meta.db_table))
        # Add the index
        index = Index(fields=['name'], name='author_title_idx')
        with connection.schema_editor() as editor:
            editor.add_index(Author, index)
        self.assertIn('name', self.get_indexes(Author._meta.db_table))
        # Drop the index
        with connection.schema_editor() as editor:
            editor.remove_index(Author, index)
        self.assertNotIn('name', self.get_indexes(Author._meta.db_table))

    def test_order_index(self):
        """
        Indexes defined with ordering (ASC/DESC) defined on column
        """
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # The table doesn't have an index
        self.assertNotIn('title', self.get_indexes(Author._meta.db_table))
        index_name = 'author_name_idx'
        # Add the index
        index = Index(fields=['name', '-weight'], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(Author, index)
        if connection.features.supports_index_column_ordering:
            if connection.features.uppercases_column_names:
                index_name = index_name.upper()
            self.assertIndexOrder(Author._meta.db_table, index_name, ['ASC', 'DESC'])

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
            self.get_indexes(Book._meta.db_table),
        )
        # Alter to remove the index
        old_field = Book._meta.get_field("title")
        new_field = CharField(max_length=100, db_index=False)
        new_field.set_attributes_from_name("title")
        with connection.schema_editor() as editor:
            editor.alter_field(Book, old_field, new_field, strict=True)
        # Ensure the table is there and has no index
        self.assertNotIn(
            "title",
            self.get_indexes(Book._meta.db_table),
        )
        # Alter to re-add the index
        new_field2 = Book._meta.get_field("title")
        with connection.schema_editor() as editor:
            editor.alter_field(Book, new_field, new_field2, strict=True)
        # Ensure the table is there and has the index again
        self.assertIn(
            "title",
            self.get_indexes(Book._meta.db_table),
        )
        # Add a unique column, verify that creates an implicit index
        new_field3 = BookWithSlug._meta.get_field("slug")
        with connection.schema_editor() as editor:
            editor.add_field(Book, new_field3)
        self.assertIn(
            "slug",
            self.get_indexes(Book._meta.db_table),
        )
        # Remove the unique, check the index goes with it
        new_field4 = CharField(max_length=20, unique=False)
        new_field4.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithSlug, new_field3, new_field4, strict=True)
        self.assertNotIn(
            "slug",
            self.get_indexes(Book._meta.db_table),
        )

    def test_primary_key(self):
        """
        Tests altering of the primary key
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
        # Ensure the table is there and has the right PK
        self.assertEqual(self.get_primary_key(Tag._meta.db_table), 'id')
        # Alter to change the PK
        id_field = Tag._meta.get_field("id")
        old_field = Tag._meta.get_field("slug")
        new_field = SlugField(primary_key=True)
        new_field.set_attributes_from_name("slug")
        new_field.model = Tag
        with connection.schema_editor() as editor:
            editor.remove_field(Tag, id_field)
            editor.alter_field(Tag, old_field, new_field)
        # Ensure the PK changed
        self.assertNotIn(
            'id',
            self.get_indexes(Tag._meta.db_table),
        )
        self.assertEqual(self.get_primary_key(Tag._meta.db_table), 'slug')

    def test_context_manager_exit(self):
        """
        Ensures transaction is correctly closed when an error occurs
        inside a SchemaEditor context.
        """
        class SomeError(Exception):
            pass
        try:
            with connection.schema_editor():
                raise SomeError
        except SomeError:
            self.assertFalse(connection.in_atomic_block)

    @skipIfDBFeature('can_rollback_ddl')
    def test_unsupported_transactional_ddl_disallowed(self):
        message = (
            "Executing DDL statements while in a transaction on databases "
            "that can't perform a rollback is prohibited."
        )
        with atomic(), connection.schema_editor() as editor:
            with self.assertRaisesMessage(TransactionManagementError, message):
                editor.execute(editor.sql_create_table % {'table': 'foo', 'definition': ''})

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_foreign_key_index_long_names_regression(self):
        """
        Regression test for #21497.
        Only affects databases that supports foreign keys.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithEvenLongerName)
            editor.create_model(BookWithLongName)
        # Find the properly shortened column name
        column_name = connection.ops.quote_name("author_foreign_key_with_really_long_field_name_id")
        column_name = column_name[1:-1].lower()  # unquote, and, for Oracle, un-upcase
        # Ensure the table is there and has an index on the column
        self.assertIn(
            column_name,
            self.get_indexes(BookWithLongName._meta.db_table),
        )

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_add_foreign_key_long_names(self):
        """
        Regression test for #23009.
        Only affects databases that supports foreign keys.
        """
        # Create the initial tables
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithEvenLongerName)
            editor.create_model(BookWithLongName)
        # Add a second FK, this would fail due to long ref name before the fix
        new_field = ForeignKey(AuthorWithEvenLongerName, CASCADE, related_name="something")
        new_field.set_attributes_from_name("author_other_really_long_named_i_mean_so_long_fk")
        with connection.schema_editor() as editor:
            editor.add_field(BookWithLongName, new_field)

    def test_add_foreign_object(self):
        with connection.schema_editor() as editor:
            editor.create_model(BookForeignObj)

        new_field = ForeignObject(Author, on_delete=CASCADE, from_fields=['author_id'], to_fields=['id'])
        new_field.set_attributes_from_name('author')
        with connection.schema_editor() as editor:
            editor.add_field(BookForeignObj, new_field)

    def test_creation_deletion_reserved_names(self):
        """
        Tries creating a model's table, and then deleting it when it has a
        SQL reserved name.
        """
        # Create the table
        with connection.schema_editor() as editor:
            try:
                editor.create_model(Thing)
            except OperationalError as e:
                self.fail("Errors when applying initial migration for a model "
                          "with a table named after an SQL reserved word: %s" % e)
        # The table is there
        list(Thing.objects.all())
        # Clean up that table
        with connection.schema_editor() as editor:
            editor.delete_model(Thing)
        # The table is gone
        with self.assertRaises(DatabaseError):
            list(Thing.objects.all())

    def test_remove_constraints_capital_letters(self):
        """
        #23065 - Constraint names must be quoted if they contain capital letters.
        """
        def get_field(*args, **kwargs):
            kwargs['db_column'] = "CamelCase"
            field = kwargs.pop('field_class', IntegerField)(*args, **kwargs)
            field.set_attributes_from_name("CamelCase")
            return field

        model = Author
        field = get_field()
        table = model._meta.db_table
        column = field.column

        with connection.schema_editor() as editor:
            editor.create_model(model)
            editor.add_field(model, field)

            constraint_name = "CamelCaseIndex"
            editor.execute(
                editor.sql_create_index % {
                    "table": editor.quote_name(table),
                    "name": editor.quote_name(constraint_name),
                    "using": "",
                    "columns": editor.quote_name(column),
                    "extra": "",
                }
            )
            if connection.features.uppercases_column_names:
                constraint_name = constraint_name.upper()
            self.assertIn(constraint_name, self.get_constraints(model._meta.db_table))
            editor.alter_field(model, get_field(db_index=True), field, strict=True)
            self.assertNotIn(constraint_name, self.get_constraints(model._meta.db_table))

            constraint_name = "CamelCaseUniqConstraint"
            editor.execute(
                editor.sql_create_unique % {
                    "table": editor.quote_name(table),
                    "name": editor.quote_name(constraint_name),
                    "columns": editor.quote_name(field.column),
                }
            )
            if connection.features.uppercases_column_names:
                constraint_name = constraint_name.upper()
            self.assertIn(constraint_name, self.get_constraints(model._meta.db_table))
            editor.alter_field(model, get_field(unique=True), field, strict=True)
            self.assertNotIn(constraint_name, self.get_constraints(model._meta.db_table))

            if connection.features.supports_foreign_keys:
                constraint_name = "CamelCaseFKConstraint"
                editor.execute(
                    editor.sql_create_fk % {
                        "table": editor.quote_name(table),
                        "name": editor.quote_name(constraint_name),
                        "column": editor.quote_name(column),
                        "to_table": editor.quote_name(table),
                        "to_column": editor.quote_name(model._meta.auto_field.column),
                        "deferrable": connection.ops.deferrable_sql(),
                    }
                )
                if connection.features.uppercases_column_names:
                    constraint_name = constraint_name.upper()
                self.assertIn(constraint_name, self.get_constraints(model._meta.db_table))
                editor.alter_field(model, get_field(Author, CASCADE, field_class=ForeignKey), field, strict=True)
                self.assertNotIn(constraint_name, self.get_constraints(model._meta.db_table))

    def test_add_field_use_effective_default(self):
        """
        #23987 - effective_default() should be used as the field default when
        adding a new field.
        """
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure there's no surname field
        columns = self.column_classes(Author)
        self.assertNotIn("surname", columns)
        # Create a row
        Author.objects.create(name='Anonymous1')
        # Add new CharField to ensure default will be used from effective_default
        new_field = CharField(max_length=15, blank=True)
        new_field.set_attributes_from_name("surname")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        # Ensure field was added with the right default
        with connection.cursor() as cursor:
            cursor.execute("SELECT surname FROM schema_author;")
            item = cursor.fetchall()[0]
            self.assertEqual(item[0], None if connection.features.interprets_empty_strings_as_nulls else '')

    def test_add_field_default_dropped(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Ensure there's no surname field
        columns = self.column_classes(Author)
        self.assertNotIn("surname", columns)
        # Create a row
        Author.objects.create(name='Anonymous1')
        # Add new CharField with a default
        new_field = CharField(max_length=15, blank=True, default='surname default')
        new_field.set_attributes_from_name("surname")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        # Ensure field was added with the right default
        with connection.cursor() as cursor:
            cursor.execute("SELECT surname FROM schema_author;")
            item = cursor.fetchall()[0]
            self.assertEqual(item[0], 'surname default')
            # And that the default is no longer set in the database.
            field = next(
                f for f in connection.introspection.get_table_description(cursor, "schema_author")
                if f.name == "surname"
            )
            if connection.features.can_introspect_default:
                self.assertIsNone(field.default)

    def test_alter_field_default_dropped(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Create a row
        Author.objects.create(name='Anonymous1')
        self.assertIsNone(Author.objects.get().height)
        old_field = Author._meta.get_field('height')
        # The default from the new field is used in updating existing rows.
        new_field = IntegerField(blank=True, default=42)
        new_field.set_attributes_from_name('height')
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        self.assertEqual(Author.objects.get().height, 42)
        # The database default should be removed.
        with connection.cursor() as cursor:
            field = next(
                f for f in connection.introspection.get_table_description(cursor, "schema_author")
                if f.name == "height"
            )
            if connection.features.can_introspect_default:
                self.assertIsNone(field.default)

    def test_add_textfield_unhashable_default(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Create a row
        Author.objects.create(name='Anonymous1')
        # Create a field that has an unhashable default
        new_field = TextField(default={})
        new_field.set_attributes_from_name("info")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_add_indexed_charfield(self):
        field = CharField(max_length=255, db_index=True)
        field.set_attributes_from_name('nom_de_plume')
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.add_field(Author, field)
        # Should create two indexes; one for like operator.
        self.assertEqual(
            self.get_constraints_for_column(Author, 'nom_de_plume'),
            ['schema_author_nom_de_plume_7570a851', 'schema_author_nom_de_plume_7570a851_like'],
        )

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_add_unique_charfield(self):
        field = CharField(max_length=255, unique=True)
        field.set_attributes_from_name('nom_de_plume')
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.add_field(Author, field)
        # Should create two indexes; one for like operator.
        self.assertEqual(
            self.get_constraints_for_column(Author, 'nom_de_plume'),
            ['schema_author_nom_de_plume_7570a851_like', 'schema_author_nom_de_plume_key']
        )

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_alter_field_add_index_to_charfield(self):
        # Create the table and verify no initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        self.assertEqual(self.get_constraints_for_column(Author, 'name'), [])
        # Alter to add db_index=True and create 2 indexes.
        old_field = Author._meta.get_field('name')
        new_field = CharField(max_length=255, db_index=True)
        new_field.set_attributes_from_name('name')
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(Author, 'name'),
            ['schema_author_name_1fbc5617', 'schema_author_name_1fbc5617_like']
        )
        # Remove db_index=True to drop both indexes.
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, old_field, strict=True)
        self.assertEqual(self.get_constraints_for_column(Author, 'name'), [])

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_alter_field_add_unique_to_charfield(self):
        # Create the table and verify no initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        self.assertEqual(self.get_constraints_for_column(Author, 'name'), [])
        # Alter to add unique=True and create 2 indexes.
        old_field = Author._meta.get_field('name')
        new_field = CharField(max_length=255, unique=True)
        new_field.set_attributes_from_name('name')
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(Author, 'name'),
            ['schema_author_name_1fbc5617_like', 'schema_author_name_1fbc5617_uniq']
        )
        # Remove unique=True to drop both indexes.
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, old_field, strict=True)
        self.assertEqual(self.get_constraints_for_column(Author, 'name'), [])

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_alter_field_add_index_to_textfield(self):
        # Create the table and verify no initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(Note)
        self.assertEqual(self.get_constraints_for_column(Note, 'info'), [])
        # Alter to add db_index=True and create 2 indexes.
        old_field = Note._meta.get_field('info')
        new_field = TextField(db_index=True)
        new_field.set_attributes_from_name('info')
        with connection.schema_editor() as editor:
            editor.alter_field(Note, old_field, new_field, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(Note, 'info'),
            ['schema_note_info_4b0ea695', 'schema_note_info_4b0ea695_like']
        )
        # Remove db_index=True to drop both indexes.
        with connection.schema_editor() as editor:
            editor.alter_field(Note, new_field, old_field, strict=True)
        self.assertEqual(self.get_constraints_for_column(Note, 'info'), [])

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_alter_field_add_unique_to_charfield_with_db_index(self):
        # Create the table and verify initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(BookWithoutAuthor)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff', 'schema_book_title_2dfb2dff_like']
        )
        # Alter to add unique=True (should replace the index)
        old_field = BookWithoutAuthor._meta.get_field('title')
        new_field = CharField(max_length=100, db_index=True, unique=True)
        new_field.set_attributes_from_name('title')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithoutAuthor, old_field, new_field, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff_like', 'schema_book_title_2dfb2dff_uniq']
        )
        # Alter to remove unique=True (should drop unique index)
        new_field2 = CharField(max_length=100, db_index=True)
        new_field2.set_attributes_from_name('title')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithoutAuthor, new_field, new_field2, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff', 'schema_book_title_2dfb2dff_like']
        )

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_alter_field_remove_unique_and_db_index_from_charfield(self):
        # Create the table and verify initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(BookWithoutAuthor)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff', 'schema_book_title_2dfb2dff_like']
        )
        # Alter to add unique=True (should replace the index)
        old_field = BookWithoutAuthor._meta.get_field('title')
        new_field = CharField(max_length=100, db_index=True, unique=True)
        new_field.set_attributes_from_name('title')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithoutAuthor, old_field, new_field, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff_like', 'schema_book_title_2dfb2dff_uniq']
        )
        # Alter to remove both unique=True and db_index=True (should drop all indexes)
        new_field2 = CharField(max_length=100)
        new_field2.set_attributes_from_name('title')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithoutAuthor, new_field, new_field2, strict=True)
        self.assertEqual(self.get_constraints_for_column(BookWithoutAuthor, 'title'), [])

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_alter_field_swap_unique_and_db_index_with_charfield(self):
        # Create the table and verify initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(BookWithoutAuthor)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff', 'schema_book_title_2dfb2dff_like']
        )
        # Alter to set unique=True and remove db_index=True (should replace the index)
        old_field = BookWithoutAuthor._meta.get_field('title')
        new_field = CharField(max_length=100, unique=True)
        new_field.set_attributes_from_name('title')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithoutAuthor, old_field, new_field, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff_like', 'schema_book_title_2dfb2dff_uniq']
        )
        # Alter to set db_index=True and remove unique=True (should restore index)
        new_field2 = CharField(max_length=100, db_index=True)
        new_field2.set_attributes_from_name('title')
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithoutAuthor, new_field, new_field2, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(BookWithoutAuthor, 'title'),
            ['schema_book_title_2dfb2dff', 'schema_book_title_2dfb2dff_like']
        )

    @unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific")
    def test_alter_field_add_db_index_to_charfield_with_unique(self):
        # Create the table and verify initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
        self.assertEqual(
            self.get_constraints_for_column(Tag, 'slug'),
            ['schema_tag_slug_2c418ba3_like', 'schema_tag_slug_key']
        )
        # Alter to add db_index=True
        old_field = Tag._meta.get_field('slug')
        new_field = SlugField(db_index=True, unique=True)
        new_field.set_attributes_from_name('slug')
        with connection.schema_editor() as editor:
            editor.alter_field(Tag, old_field, new_field, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(Tag, 'slug'),
            ['schema_tag_slug_2c418ba3_like', 'schema_tag_slug_key']
        )
        # Alter to remove db_index=True
        new_field2 = SlugField(unique=True)
        new_field2.set_attributes_from_name('slug')
        with connection.schema_editor() as editor:
            editor.alter_field(Tag, new_field, new_field2, strict=True)
        self.assertEqual(
            self.get_constraints_for_column(Tag, 'slug'),
            ['schema_tag_slug_2c418ba3_like', 'schema_tag_slug_key']
        )

    def test_alter_field_add_index_to_integerfield(self):
        # Create the table and verify no initial indexes.
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        self.assertEqual(self.get_constraints_for_column(Author, 'weight'), [])

        # Alter to add db_index=True and create index.
        old_field = Author._meta.get_field('weight')
        new_field = IntegerField(null=True, db_index=True)
        new_field.set_attributes_from_name('weight')
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)

        expected = 'schema_author_weight_587740f9'
        if connection.features.uppercases_column_names:
            expected = expected.upper()
        self.assertEqual(self.get_constraints_for_column(Author, 'weight'), [expected])

        # Remove db_index=True to drop index.
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, old_field, strict=True)
        self.assertEqual(self.get_constraints_for_column(Author, 'weight'), [])

    def test_alter_pk_with_self_referential_field(self):
        """
        Changing the primary key field name of a model with a self-referential
        foreign key (#26384).
        """
        if connection.vendor == 'mysql' and connection.mysql_version < (5, 6, 6):
            self.skipTest('Skip known bug renaming primary keys on older MySQL versions (#24995).')
        with connection.schema_editor() as editor:
            editor.create_model(Node)
        old_field = Node._meta.get_field('node_id')
        new_field = AutoField(primary_key=True)
        new_field.set_attributes_from_name('id')
        with connection.schema_editor() as editor:
            editor.alter_field(Node, old_field, new_field, strict=True)

    @mock.patch('django.db.backends.base.schema.datetime')
    @mock.patch('django.db.backends.base.schema.timezone')
    def test_add_datefield_and_datetimefield_use_effective_default(self, mocked_datetime, mocked_tz):
        """
        effective_default() should be used for DateField, DateTimeField, and
        TimeField if auto_now or auto_add_now is set (#25005).
        """
        now = datetime.datetime(month=1, day=1, year=2000, hour=1, minute=1)
        now_tz = datetime.datetime(month=1, day=1, year=2000, hour=1, minute=1, tzinfo=timezone.utc)
        mocked_datetime.now = mock.MagicMock(return_value=now)
        mocked_tz.now = mock.MagicMock(return_value=now_tz)
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Check auto_now/auto_now_add attributes are not defined
        columns = self.column_classes(Author)
        self.assertNotIn("dob_auto_now", columns)
        self.assertNotIn("dob_auto_now_add", columns)
        self.assertNotIn("dtob_auto_now", columns)
        self.assertNotIn("dtob_auto_now_add", columns)
        self.assertNotIn("tob_auto_now", columns)
        self.assertNotIn("tob_auto_now_add", columns)
        # Create a row
        Author.objects.create(name='Anonymous1')
        # Ensure fields were added with the correct defaults
        dob_auto_now = DateField(auto_now=True)
        dob_auto_now.set_attributes_from_name('dob_auto_now')
        self.check_added_field_default(
            editor, Author, dob_auto_now, 'dob_auto_now', now.date(),
            cast_function=lambda x: x.date(),
        )
        dob_auto_now_add = DateField(auto_now_add=True)
        dob_auto_now_add.set_attributes_from_name('dob_auto_now_add')
        self.check_added_field_default(
            editor, Author, dob_auto_now_add, 'dob_auto_now_add', now.date(),
            cast_function=lambda x: x.date(),
        )
        dtob_auto_now = DateTimeField(auto_now=True)
        dtob_auto_now.set_attributes_from_name('dtob_auto_now')
        self.check_added_field_default(
            editor, Author, dtob_auto_now, 'dtob_auto_now', now,
        )
        dt_tm_of_birth_auto_now_add = DateTimeField(auto_now_add=True)
        dt_tm_of_birth_auto_now_add.set_attributes_from_name('dtob_auto_now_add')
        self.check_added_field_default(
            editor, Author, dt_tm_of_birth_auto_now_add, 'dtob_auto_now_add', now,
        )
        tob_auto_now = TimeField(auto_now=True)
        tob_auto_now.set_attributes_from_name('tob_auto_now')
        self.check_added_field_default(
            editor, Author, tob_auto_now, 'tob_auto_now', now.time(),
            cast_function=lambda x: x.time(),
        )
        tob_auto_now_add = TimeField(auto_now_add=True)
        tob_auto_now_add.set_attributes_from_name('tob_auto_now_add')
        self.check_added_field_default(
            editor, Author, tob_auto_now_add, 'tob_auto_now_add', now.time(),
            cast_function=lambda x: x.time(),
        )

    @unittest.skipUnless(connection.vendor == 'oracle', 'Oracle specific db_table syntax')
    def test_creation_with_db_table_double_quotes(self):
        oracle_user = connection.creation._test_database_user()

        class Student(Model):
            name = CharField(max_length=30)

            class Meta:
                app_label = 'schema'
                apps = new_apps
                db_table = '"%s"."DJANGO_STUDENT_TABLE"' % oracle_user

        class Document(Model):
            name = CharField(max_length=30)
            students = ManyToManyField(Student)

            class Meta:
                app_label = 'schema'
                apps = new_apps
                db_table = '"%s"."DJANGO_DOCUMENT_TABLE"' % oracle_user

        self.local_models = [Student, Document]

        with connection.schema_editor() as editor:
            editor.create_model(Student)
            editor.create_model(Document)

        doc = Document.objects.create(name='Test Name')
        student = Student.objects.create(name='Some man')
        doc.students.add(student)
