import datetime
import itertools
import unittest
from copy import copy
from unittest import mock

from django.db import (
    DatabaseError, IntegrityError, OperationalError, connection,
)
from django.db.models import Model, Q
from django.db.models.constraints import CheckConstraint, UniqueConstraint
from django.db.models.deletion import CASCADE, PROTECT
from django.db.models.fields import (
    AutoField, BigAutoField, BigIntegerField, BinaryField, BooleanField,
    CharField, DateField, DateTimeField, IntegerField, PositiveIntegerField,
    SlugField, TextField, TimeField, UUIDField,
)
from django.db.models.fields.related import (
    ForeignKey, ForeignObject, ManyToManyField, OneToOneField,
)
from django.db.models.indexes import Index
from django.db.transaction import TransactionManagementError, atomic
from django.test import (
    TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature,
)
from django.test.utils import CaptureQueriesContext, isolate_apps
from django.utils import timezone

from .fields import (
    CustomManyToManyField, InheritedManyToManyField, MediumBlobField,
)
from .models import (
    Author, AuthorCharFieldWithIndex, AuthorTextFieldWithIndex,
    AuthorWithDefaultHeight, AuthorWithEvenLongerName, AuthorWithIndexedName,
    AuthorWithIndexedNameAndBirthday, AuthorWithUniqueName,
    AuthorWithUniqueNameAndBirthday, Book, BookForeignObj, BookWeak,
    BookWithLongName, BookWithO2O, BookWithoutAuthor, BookWithSlug, IntegerPK,
    Node, Note, NoteRename, Tag, TagIndexed, TagM2MTest, TagUniqueRename,
    Thing, UniqueTest, new_apps,
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
        Author, AuthorCharFieldWithIndex, AuthorTextFieldWithIndex,
        AuthorWithDefaultHeight, AuthorWithEvenLongerName, Book, BookWeak,
        BookWithLongName, BookWithO2O, BookWithSlug, IntegerPK, Node, Note,
        Tag, TagIndexed, TagM2MTest, TagUniqueRename, Thing, UniqueTest,
    ]

    # Utility functions

    def setUp(self):
        # local_models should contain test dependent model classes that will be
        # automatically removed from the app cache on test tear down.
        self.local_models = []
        # isolated_local_models contains models that are in test methods
        # decorated with @isolate_apps.
        self.isolated_local_models = []

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
        if self.isolated_local_models:
            with connection.schema_editor() as editor:
                for model in self.isolated_local_models:
                    editor.delete_model(model)

    def delete_tables(self):
        "Deletes all model tables for our models for a clean test environment"
        converter = connection.introspection.identifier_converter
        with connection.schema_editor() as editor:
            connection.disable_constraint_checking()
            table_names = connection.introspection.table_names()
            if connection.features.ignores_table_name_case:
                table_names = [table_name.lower() for table_name in table_names]
            for model in itertools.chain(SchemaTests.models, self.local_models):
                tbl = converter(model._meta.db_table)
                if connection.features.ignores_table_name_case:
                    tbl = tbl.lower()
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

    def get_uniques(self, table):
        with connection.cursor() as cursor:
            return [
                c['columns'][0]
                for c in connection.introspection.get_constraints(cursor, table).values()
                if c['unique'] and len(c['columns']) == 1
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
        self.assertTrue(all(val == expected for val, expected in zip(index_orders, order)))

    def assertForeignKeyExists(self, model, column, expected_fk_table, field='id'):
        """
        Fail if the FK constraint on `model.Meta.db_table`.`column` to
        `expected_fk_table`.id doesn't exist.
        """
        constraints = self.get_constraints(model._meta.db_table)
        constraint_fk = None
        for details in constraints.values():
            if details['columns'] == [column] and details['foreign_key']:
                constraint_fk = details['foreign_key']
                break
        self.assertEqual(constraint_fk, (expected_fk_table, field))

    def assertForeignKeyNotExists(self, model, column, expected_fk_table):
        with self.assertRaises(AssertionError):
            self.assertForeignKeyExists(model, column, expected_fk_table)

    # Tests
    def test_creation_deletion(self):
        """
        Tries creating a model's table, and then deleting it.
        """
        with connection.schema_editor() as editor:
            # Create the table
            editor.create_model(Author)
            # The table is there
            list(Author.objects.all())
            # Clean up that table
            editor.delete_model(Author)
            # No deferred SQL should be left over.
            self.assertEqual(editor.deferred_sql, [])
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
        self.assertForeignKeyExists(Book, 'author_id', 'schema_tag')

    @skipUnlessDBFeature('supports_foreign_keys')
    def test_char_field_with_db_index_to_fk(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(AuthorCharFieldWithIndex)
        # Change CharField to FK
        old_field = AuthorCharFieldWithIndex._meta.get_field('char_field')
        new_field = ForeignKey(Author, CASCADE, blank=True)
        new_field.set_attributes_from_name('char_field')
        with connection.schema_editor() as editor:
            editor.alter_field(AuthorCharFieldWithIndex, old_field, new_field, strict=True)
        self.assertForeignKeyExists(AuthorCharFieldWithIndex, 'char_field_id', 'schema_author')

    @skipUnlessDBFeature('supports_foreign_keys')
    @skipUnlessDBFeature('supports_index_on_text_field')
    def test_text_field_with_db_index_to_fk(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(AuthorTextFieldWithIndex)
        # Change TextField to FK
        old_field = AuthorTextFieldWithIndex._meta.get_field('text_field')
        new_field = ForeignKey(Author, CASCADE, blank=True)
        new_field.set_attributes_from_name('text_field')
        with connection.schema_editor() as editor:
            editor.alter_field(AuthorTextFieldWithIndex, old_field, new_field, strict=True)
        self.assertForeignKeyExists(AuthorTextFieldWithIndex, 'text_field_id', 'schema_author')

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
        self.assertForeignKeyExists(AuthorRef, 'author_id', 'schema_author')

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
        self.assertForeignKeyNotExists(BookWeak, 'author_id', 'schema_author')
        # Make a db_constraint=False FK
        new_field = ForeignKey(Tag, CASCADE, db_constraint=False)
        new_field.set_attributes_from_name("tag")
        with connection.schema_editor() as editor:
            editor.add_field(Author, new_field)
        self.assertForeignKeyNotExists(Author, 'tag_id', 'schema_tag')
        # Alter to one with a constraint
        new_field2 = ForeignKey(Tag, CASCADE)
        new_field2.set_attributes_from_name("tag")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, new_field2, strict=True)
        self.assertForeignKeyExists(Author, 'tag_id', 'schema_tag')
        # Alter to one without a constraint again
        new_field2 = ForeignKey(Tag, CASCADE)
        new_field2.set_attributes_from_name("tag")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field2, new_field, strict=True)
        self.assertForeignKeyNotExists(Author, 'tag_id', 'schema_tag')

    @isolate_apps('schema')
    def test_no_db_constraint_added_during_primary_key_change(self):
        """
        When a primary key that's pointed to by a ForeignKey with
        db_constraint=False is altered, a foreign key constraint isn't added.
        """
        class Author(Model):
            class Meta:
                app_label = 'schema'

        class BookWeak(Model):
            author = ForeignKey(Author, CASCADE, db_constraint=False)

            class Meta:
                app_label = 'schema'

        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(BookWeak)
        self.assertForeignKeyNotExists(BookWeak, 'author_id', 'schema_author')
        old_field = Author._meta.get_field('id')
        new_field = BigAutoField(primary_key=True)
        new_field.model = Author
        new_field.set_attributes_from_name('id')
        # @isolate_apps() and inner models are needed to have the model
        # relations populated, otherwise this doesn't act as a regression test.
        self.assertEqual(len(new_field.model._meta.related_objects), 1)
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        self.assertForeignKeyNotExists(BookWeak, 'author_id', 'schema_author')

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
        self.assertForeignKeyNotExists(new_field.remote_field.through, 'tag_id', 'schema_tag')

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

    def test_add_field_remove_field(self):
        """
        Adding a field and removing it removes all deferred sql referring to it.
        """
        with connection.schema_editor() as editor:
            # Create a table with a unique constraint on the slug field.
            editor.create_model(Tag)
            # Remove the slug column.
            editor.remove_field(Tag, Tag._meta.get_field('slug'))
        self.assertEqual(editor.deferred_sql, [])

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
        self.assertEqual(field_type, connection.features.introspected_boolean_field_type)

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

    def test_alter_auto_field_to_integer_field(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Change AutoField to IntegerField
        old_field = Author._meta.get_field('id')
        new_field = IntegerField(primary_key=True)
        new_field.set_attributes_from_name('id')
        new_field.model = Author
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)

    def test_alter_auto_field_to_char_field(self):
        # Create the table
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Change AutoField to CharField
        old_field = Author._meta.get_field('id')
        new_field = CharField(primary_key=True, max_length=50)
        new_field.set_attributes_from_name('id')
        new_field.model = Author
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)

    def test_alter_not_unique_field_to_primary_key(self):
        # Create the table.
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Change UUIDField to primary key.
        old_field = Author._meta.get_field('uuid')
        new_field = UUIDField(primary_key=True)
        new_field.set_attributes_from_name('uuid')
        new_field.model = Author
        with connection.schema_editor() as editor:
            editor.remove_field(Author, Author._meta.get_field('id'))
            editor.alter_field(Author, old_field, new_field, strict=True)

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
        self.assertForeignKeyExists(Book, 'author_id', 'schema_author')
        # Alter the FK
        old_field = Book._meta.get_field("author")
        new_field = ForeignKey(Author, CASCADE, editable=False)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(Book, old_field, new_field, strict=True)
        # Ensure the field is right afterwards
        columns = self.column_classes(Book)
        self.assertEqual(columns['author_id'][0], "IntegerField")
        self.assertForeignKeyExists(Book, 'author_id', 'schema_author')

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
        for details in constraints.values():
            if details['foreign_key']:
                self.fail('Found an unexpected FK constraint to %s' % details['columns'])
        old_field = LocalBook._meta.get_field("author")
        new_field = ForeignKey(Author, CASCADE)
        new_field.set_attributes_from_name("author")
        with connection.schema_editor() as editor:
            editor.alter_field(LocalBook, old_field, new_field, strict=True)
        self.assertForeignKeyExists(LocalBook, 'author_id', 'schema_author')

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
        self.assertForeignKeyExists(BookWithO2O, 'author_id', 'schema_author')
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
        self.assertForeignKeyExists(Book, 'author_id', 'schema_author')

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
        self.assertForeignKeyExists(Book, 'author_id', 'schema_author')
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
        self.assertForeignKeyExists(BookWithO2O, 'author_id', 'schema_author')

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

    def test_alter_int_pk_to_bigautofield_pk(self):
        """
        Should be able to rename an IntegerField(primary_key=True) to
        BigAutoField(primary_key=True).
        """
        with connection.schema_editor() as editor:
            editor.create_model(IntegerPK)

        old_field = IntegerPK._meta.get_field('i')
        new_field = BigAutoField(primary_key=True)
        new_field.model = IntegerPK
        new_field.set_attributes_from_name('i')

        with connection.schema_editor() as editor:
            editor.alter_field(IntegerPK, old_field, new_field, strict=True)

    def test_alter_int_pk_to_int_unique(self):
        """
        Should be able to rename an IntegerField(primary_key=True) to
        IntegerField(unique=True).
        """
        with connection.schema_editor() as editor:
            editor.create_model(IntegerPK)
        # Delete the old PK
        old_field = IntegerPK._meta.get_field('i')
        new_field = IntegerField(unique=True)
        new_field.model = IntegerPK
        new_field.set_attributes_from_name('i')
        with connection.schema_editor() as editor:
            editor.alter_field(IntegerPK, old_field, new_field, strict=True)
        # The primary key constraint is gone. Result depends on database:
        # 'id' for SQLite, None for others (must not be 'i').
        self.assertIn(self.get_primary_key(IntegerPK._meta.db_table), ('id', None))

        # Set up a model class as it currently stands. The original IntegerPK
        # class is now out of date and some backends make use of the whole
        # model class when modifying a field (such as sqlite3 when remaking a
        # table) so an outdated model class leads to incorrect results.
        class Transitional(Model):
            i = IntegerField(unique=True)
            j = IntegerField(unique=True)

            class Meta:
                app_label = 'schema'
                apps = new_apps
                db_table = 'INTEGERPK'

        # model requires a new PK
        old_field = Transitional._meta.get_field('j')
        new_field = IntegerField(primary_key=True)
        new_field.model = Transitional
        new_field.set_attributes_from_name('j')

        with connection.schema_editor() as editor:
            editor.alter_field(Transitional, old_field, new_field, strict=True)

        # Create a model class representing the updated model.
        class IntegerUnique(Model):
            i = IntegerField(unique=True)
            j = IntegerField(primary_key=True)

            class Meta:
                app_label = 'schema'
                apps = new_apps
                db_table = 'INTEGERPK'

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

    @isolate_apps('schema')
    def test_rename_referenced_field(self):
        class Author(Model):
            name = CharField(max_length=255, unique=True)

            class Meta:
                app_label = 'schema'

        class Book(Model):
            author = ForeignKey(Author, CASCADE, to_field='name')

            class Meta:
                app_label = 'schema'

        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        new_field = CharField(max_length=255, unique=True)
        new_field.set_attributes_from_name('renamed')
        with connection.schema_editor(atomic=connection.features.supports_atomic_references_rename) as editor:
            editor.alter_field(Author, Author._meta.get_field('name'), new_field)
        # Ensure the foreign key reference was updated.
        self.assertForeignKeyExists(Book, 'author_id', 'schema_author', 'renamed')

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
        if connection.features.supports_foreign_keys:
            self.assertForeignKeyExists(
                LocalBookWithM2M._meta.get_field("tags").remote_field.through,
                'tagm2mtest_id',
                'schema_tagm2mtest',
            )
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
        if connection.features.supports_foreign_keys:
            self.assertForeignKeyExists(new_field.remote_field.through, 'uniquetest_id', 'schema_uniquetest')

    def test_m2m_repoint(self):
        self._test_m2m_repoint(ManyToManyField)

    def test_m2m_repoint_custom(self):
        self._test_m2m_repoint(CustomManyToManyField)

    def test_m2m_repoint_inherited(self):
        self._test_m2m_repoint(InheritedManyToManyField)

    @isolate_apps('schema')
    def test_m2m_rename_field_in_target_model(self):
        class LocalTagM2MTest(Model):
            title = CharField(max_length=255)

            class Meta:
                app_label = 'schema'

        class LocalM2M(Model):
            tags = ManyToManyField(LocalTagM2MTest)

            class Meta:
                app_label = 'schema'

        # Create the tables.
        with connection.schema_editor() as editor:
            editor.create_model(LocalM2M)
            editor.create_model(LocalTagM2MTest)
        self.isolated_local_models = [LocalM2M, LocalTagM2MTest]
        # Ensure the m2m table is there.
        self.assertEqual(len(self.column_classes(LocalM2M)), 1)
        # Alter a field in LocalTagM2MTest.
        old_field = LocalTagM2MTest._meta.get_field('title')
        new_field = CharField(max_length=254)
        new_field.contribute_to_class(LocalTagM2MTest, 'title1')
        # @isolate_apps() and inner models are needed to have the model
        # relations populated, otherwise this doesn't act as a regression test.
        self.assertEqual(len(new_field.model._meta.related_objects), 1)
        with connection.schema_editor() as editor:
            editor.alter_field(LocalTagM2MTest, old_field, new_field, strict=True)
        # Ensure the m2m table is still there.
        self.assertEqual(len(self.column_classes(LocalM2M)), 1)

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
        if not any(details['columns'] == ['height'] and details['check'] for details in constraints.values()):
            self.fail("No check constraint for height found")
        # Alter the column to remove it
        old_field = Author._meta.get_field("height")
        new_field = IntegerField(null=True, blank=True)
        new_field.set_attributes_from_name("height")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        constraints = self.get_constraints(Author._meta.db_table)
        for details in constraints.values():
            if details['columns'] == ["height"] and details['check']:
                self.fail("Check constraint for height found")
        # Alter the column to re-add it
        new_field2 = Author._meta.get_field("height")
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, new_field2, strict=True)
        constraints = self.get_constraints(Author._meta.db_table)
        if not any(details['columns'] == ['height'] and details['check'] for details in constraints.values()):
            self.fail("No check constraint for height found")

    @skipUnlessDBFeature('supports_column_check_constraints')
    def test_remove_field_check_does_not_remove_meta_constraints(self):
        with connection.schema_editor() as editor:
            editor.create_model(Author)
        # Add the custom check constraint
        constraint = CheckConstraint(check=Q(height__gte=0), name='author_height_gte_0_check')
        custom_constraint_name = constraint.name
        Author._meta.constraints = [constraint]
        with connection.schema_editor() as editor:
            editor.add_constraint(Author, constraint)
        # Ensure the constraints exist
        constraints = self.get_constraints(Author._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['height'] and details['check'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Alter the column to remove field check
        old_field = Author._meta.get_field('height')
        new_field = IntegerField(null=True, blank=True)
        new_field.set_attributes_from_name('height')
        with connection.schema_editor() as editor:
            editor.alter_field(Author, old_field, new_field, strict=True)
        constraints = self.get_constraints(Author._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['height'] and details['check'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 0)
        # Alter the column to re-add field check
        new_field2 = Author._meta.get_field('height')
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, new_field2, strict=True)
        constraints = self.get_constraints(Author._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['height'] and details['check'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Drop the check constraint
        with connection.schema_editor() as editor:
            Author._meta.constraints = []
            editor.remove_constraint(Author, constraint)

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

    def test_unique_name_quoting(self):
        old_table_name = TagUniqueRename._meta.db_table
        try:
            with connection.schema_editor() as editor:
                editor.create_model(TagUniqueRename)
                editor.alter_db_table(TagUniqueRename, old_table_name, 'unique-table')
                TagUniqueRename._meta.db_table = 'unique-table'
                # This fails if the unique index name isn't quoted.
                editor.alter_unique_together(TagUniqueRename, [], (('title', 'slug2'),))
        finally:
            TagUniqueRename._meta.db_table = old_table_name

    @isolate_apps('schema')
    @unittest.skipIf(connection.vendor == 'sqlite', 'SQLite naively remakes the table on field alteration.')
    @skipUnlessDBFeature('supports_foreign_keys')
    def test_unique_no_unnecessary_fk_drops(self):
        """
        If AlterField isn't selective about dropping foreign key constraints
        when modifying a field with a unique constraint, the AlterField
        incorrectly drops and recreates the Book.author foreign key even though
        it doesn't restrict the field being changed (#29193).
        """
        class Author(Model):
            name = CharField(max_length=254, unique=True)

            class Meta:
                app_label = 'schema'

        class Book(Model):
            author = ForeignKey(Author, CASCADE)

            class Meta:
                app_label = 'schema'

        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        new_field = CharField(max_length=255, unique=True)
        new_field.model = Author
        new_field.set_attributes_from_name('name')
        with self.assertLogs('django.db.backends.schema', 'DEBUG') as cm:
            with connection.schema_editor() as editor:
                editor.alter_field(Author, Author._meta.get_field('name'), new_field)
        # One SQL statement is executed to alter the field.
        self.assertEqual(len(cm.records), 1)

    @isolate_apps('schema')
    @unittest.skipIf(connection.vendor == 'sqlite', 'SQLite remakes the table on field alteration.')
    def test_unique_and_reverse_m2m(self):
        """
        AlterField can modify a unique field when there's a reverse M2M
        relation on the model.
        """
        class Tag(Model):
            title = CharField(max_length=255)
            slug = SlugField(unique=True)

            class Meta:
                app_label = 'schema'

        class Book(Model):
            tags = ManyToManyField(Tag, related_name='books')

            class Meta:
                app_label = 'schema'

        self.isolated_local_models = [Book._meta.get_field('tags').remote_field.through]
        with connection.schema_editor() as editor:
            editor.create_model(Tag)
            editor.create_model(Book)
        new_field = SlugField(max_length=75, unique=True)
        new_field.model = Tag
        new_field.set_attributes_from_name('slug')
        with self.assertLogs('django.db.backends.schema', 'DEBUG') as cm:
            with connection.schema_editor() as editor:
                editor.alter_field(Tag, Tag._meta.get_field('slug'), new_field)
        # One SQL statement is executed to alter the field.
        self.assertEqual(len(cm.records), 1)
        # Ensure that the field is still unique.
        Tag.objects.create(title='foo', slug='foo')
        with self.assertRaises(IntegrityError):
            Tag.objects.create(title='bar', slug='foo')

    @skipUnlessDBFeature('allows_multiple_constraints_on_same_fields')
    def test_remove_field_unique_does_not_remove_meta_constraints(self):
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithUniqueName)
        # Add the custom unique constraint
        constraint = UniqueConstraint(fields=['name'], name='author_name_uniq')
        custom_constraint_name = constraint.name
        AuthorWithUniqueName._meta.constraints = [constraint]
        with connection.schema_editor() as editor:
            editor.add_constraint(AuthorWithUniqueName, constraint)
        # Ensure the constraints exist
        constraints = self.get_constraints(AuthorWithUniqueName._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name'] and details['unique'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Alter the column to remove field uniqueness
        old_field = AuthorWithUniqueName._meta.get_field('name')
        new_field = CharField(max_length=255)
        new_field.set_attributes_from_name('name')
        with connection.schema_editor() as editor:
            editor.alter_field(AuthorWithUniqueName, old_field, new_field, strict=True)
        constraints = self.get_constraints(AuthorWithUniqueName._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name'] and details['unique'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 0)
        # Alter the column to re-add field uniqueness
        new_field2 = AuthorWithUniqueName._meta.get_field('name')
        with connection.schema_editor() as editor:
            editor.alter_field(AuthorWithUniqueName, new_field, new_field2, strict=True)
        constraints = self.get_constraints(AuthorWithUniqueName._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name'] and details['unique'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Drop the unique constraint
        with connection.schema_editor() as editor:
            AuthorWithUniqueName._meta.constraints = []
            editor.remove_constraint(AuthorWithUniqueName, constraint)

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

    @skipUnlessDBFeature('allows_multiple_constraints_on_same_fields')
    def test_remove_unique_together_does_not_remove_meta_constraints(self):
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithUniqueNameAndBirthday)
        # Add the custom unique constraint
        constraint = UniqueConstraint(fields=['name', 'birthday'], name='author_name_birthday_uniq')
        custom_constraint_name = constraint.name
        AuthorWithUniqueNameAndBirthday._meta.constraints = [constraint]
        with connection.schema_editor() as editor:
            editor.add_constraint(AuthorWithUniqueNameAndBirthday, constraint)
        # Ensure the constraints exist
        constraints = self.get_constraints(AuthorWithUniqueNameAndBirthday._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name', 'birthday'] and details['unique'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Remove unique together
        unique_together = AuthorWithUniqueNameAndBirthday._meta.unique_together
        with connection.schema_editor() as editor:
            editor.alter_unique_together(AuthorWithUniqueNameAndBirthday, unique_together, [])
        constraints = self.get_constraints(AuthorWithUniqueNameAndBirthday._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name', 'birthday'] and details['unique'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 0)
        # Re-add unique together
        with connection.schema_editor() as editor:
            editor.alter_unique_together(AuthorWithUniqueNameAndBirthday, [], unique_together)
        constraints = self.get_constraints(AuthorWithUniqueNameAndBirthday._meta.db_table)
        self.assertIn(custom_constraint_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name', 'birthday'] and details['unique'] and name != custom_constraint_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Drop the unique constraint
        with connection.schema_editor() as editor:
            AuthorWithUniqueNameAndBirthday._meta.constraints = []
            editor.remove_constraint(AuthorWithUniqueNameAndBirthday, constraint)

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

    @skipUnlessDBFeature('allows_multiple_constraints_on_same_fields')
    def test_remove_index_together_does_not_remove_meta_indexes(self):
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithIndexedNameAndBirthday)
        # Add the custom index
        index = Index(fields=['name', 'birthday'], name='author_name_birthday_idx')
        custom_index_name = index.name
        AuthorWithIndexedNameAndBirthday._meta.indexes = [index]
        with connection.schema_editor() as editor:
            editor.add_index(AuthorWithIndexedNameAndBirthday, index)
        # Ensure the indexes exist
        constraints = self.get_constraints(AuthorWithIndexedNameAndBirthday._meta.db_table)
        self.assertIn(custom_index_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name', 'birthday'] and details['index'] and name != custom_index_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Remove index together
        index_together = AuthorWithIndexedNameAndBirthday._meta.index_together
        with connection.schema_editor() as editor:
            editor.alter_index_together(AuthorWithIndexedNameAndBirthday, index_together, [])
        constraints = self.get_constraints(AuthorWithIndexedNameAndBirthday._meta.db_table)
        self.assertIn(custom_index_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name', 'birthday'] and details['index'] and name != custom_index_name
        ]
        self.assertEqual(len(other_constraints), 0)
        # Re-add index together
        with connection.schema_editor() as editor:
            editor.alter_index_together(AuthorWithIndexedNameAndBirthday, [], index_together)
        constraints = self.get_constraints(AuthorWithIndexedNameAndBirthday._meta.db_table)
        self.assertIn(custom_index_name, constraints)
        other_constraints = [
            name for name, details in constraints.items()
            if details['columns'] == ['name', 'birthday'] and details['index'] and name != custom_index_name
        ]
        self.assertEqual(len(other_constraints), 1)
        # Drop the index
        with connection.schema_editor() as editor:
            AuthorWithIndexedNameAndBirthday._meta.indexes = []
            editor.remove_index(AuthorWithIndexedNameAndBirthday, index)

    @isolate_apps('schema')
    def test_db_table(self):
        """
        Tests renaming of the table
        """
        class Author(Model):
            name = CharField(max_length=255)

            class Meta:
                app_label = 'schema'

        class Book(Model):
            author = ForeignKey(Author, CASCADE)

            class Meta:
                app_label = 'schema'

        # Create the table and one referring it.
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        # Ensure the table is there to begin with
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        # Alter the table
        with connection.schema_editor(atomic=connection.features.supports_atomic_references_rename) as editor:
            editor.alter_db_table(Author, "schema_author", "schema_otherauthor")
        # Ensure the table is there afterwards
        Author._meta.db_table = "schema_otherauthor"
        columns = self.column_classes(Author)
        self.assertEqual(columns['name'][0], "CharField")
        # Ensure the foreign key reference was updated
        self.assertForeignKeyExists(Book, "author_id", "schema_otherauthor")
        # Alter the table again
        with connection.schema_editor(atomic=connection.features.supports_atomic_references_rename) as editor:
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

    def test_remove_db_index_doesnt_remove_custom_indexes(self):
        """
        Changing db_index to False doesn't remove indexes from Meta.indexes.
        """
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithIndexedName)
        # Ensure the table has its index
        self.assertIn('name', self.get_indexes(AuthorWithIndexedName._meta.db_table))

        # Add the custom index
        index = Index(fields=['-name'], name='author_name_idx')
        author_index_name = index.name
        with connection.schema_editor() as editor:
            db_index_name = editor._create_index_name(
                table_name=AuthorWithIndexedName._meta.db_table,
                column_names=('name',),
            )
        try:
            AuthorWithIndexedName._meta.indexes = [index]
            with connection.schema_editor() as editor:
                editor.add_index(AuthorWithIndexedName, index)
            old_constraints = self.get_constraints(AuthorWithIndexedName._meta.db_table)
            self.assertIn(author_index_name, old_constraints)
            self.assertIn(db_index_name, old_constraints)
            # Change name field to db_index=False
            old_field = AuthorWithIndexedName._meta.get_field('name')
            new_field = CharField(max_length=255)
            new_field.set_attributes_from_name('name')
            with connection.schema_editor() as editor:
                editor.alter_field(AuthorWithIndexedName, old_field, new_field, strict=True)
            new_constraints = self.get_constraints(AuthorWithIndexedName._meta.db_table)
            self.assertNotIn(db_index_name, new_constraints)
            # The index from Meta.indexes is still in the database.
            self.assertIn(author_index_name, new_constraints)
            # Drop the index
            with connection.schema_editor() as editor:
                editor.remove_index(AuthorWithIndexedName, index)
        finally:
            AuthorWithIndexedName._meta.indexes = []

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
            self.assertIndexOrder(Author._meta.db_table, index_name, ['ASC', 'DESC'])
        # Drop the index
        with connection.schema_editor() as editor:
            editor.remove_index(Author, index)

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
            self.get_uniques(Book._meta.db_table),
        )
        # Remove the unique, check the index goes with it
        new_field4 = CharField(max_length=20, unique=False)
        new_field4.set_attributes_from_name("slug")
        with connection.schema_editor() as editor:
            editor.alter_field(BookWithSlug, new_field3, new_field4, strict=True)
        self.assertNotIn(
            "slug",
            self.get_uniques(Book._meta.db_table),
        )

    def test_text_field_with_db_index(self):
        with connection.schema_editor() as editor:
            editor.create_model(AuthorTextFieldWithIndex)
        # The text_field index is present if the database supports it.
        assertion = self.assertIn if connection.features.supports_index_on_text_field else self.assertNotIn
        assertion('text_field', self.get_indexes(AuthorTextFieldWithIndex._meta.db_table))

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

    @isolate_apps('schema')
    @skipUnlessDBFeature('supports_foreign_keys')
    def test_add_foreign_key_quoted_db_table(self):
        class Author(Model):
            class Meta:
                db_table = '"table_author_double_quoted"'
                app_label = 'schema'

        class Book(Model):
            author = ForeignKey(Author, CASCADE)

            class Meta:
                app_label = 'schema'

        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
        if connection.vendor == 'mysql':
            self.assertForeignKeyExists(Book, 'author_id', '"table_author_double_quoted"')
        else:
            self.assertForeignKeyExists(Book, 'author_id', 'table_author_double_quoted')

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
        def get_field(*args, field_class=IntegerField, **kwargs):
            kwargs['db_column'] = "CamelCase"
            field = field_class(*args, **kwargs)
            field.set_attributes_from_name("CamelCase")
            return field

        model = Author
        field = get_field()
        table = model._meta.db_table
        column = field.column
        identifier_converter = connection.introspection.identifier_converter

        with connection.schema_editor() as editor:
            editor.create_model(model)
            editor.add_field(model, field)

            constraint_name = 'CamelCaseIndex'
            expected_constraint_name = identifier_converter(constraint_name)
            editor.execute(
                editor.sql_create_index % {
                    "table": editor.quote_name(table),
                    "name": editor.quote_name(constraint_name),
                    "using": "",
                    "columns": editor.quote_name(column),
                    "extra": "",
                    "condition": "",
                }
            )
            self.assertIn(expected_constraint_name, self.get_constraints(model._meta.db_table))
            editor.alter_field(model, get_field(db_index=True), field, strict=True)
            self.assertNotIn(expected_constraint_name, self.get_constraints(model._meta.db_table))

            constraint_name = 'CamelCaseUniqConstraint'
            expected_constraint_name = identifier_converter(constraint_name)
            editor.execute(editor._create_unique_sql(model, [field.column], constraint_name))
            self.assertIn(expected_constraint_name, self.get_constraints(model._meta.db_table))
            editor.alter_field(model, get_field(unique=True), field, strict=True)
            self.assertNotIn(expected_constraint_name, self.get_constraints(model._meta.db_table))

            if editor.sql_create_fk:
                constraint_name = 'CamelCaseFKConstraint'
                expected_constraint_name = identifier_converter(constraint_name)
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
                self.assertIn(expected_constraint_name, self.get_constraints(model._meta.db_table))
                editor.alter_field(model, get_field(Author, CASCADE, field_class=ForeignKey), field, strict=True)
                self.assertNotIn(expected_constraint_name, self.get_constraints(model._meta.db_table))

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

    @unittest.skipIf(connection.vendor == 'sqlite', 'SQLite naively remakes the table on field alteration.')
    def test_alter_field_default_doesnt_perfom_queries(self):
        """
        No queries are performed if a field default changes and the field's
        not changing from null to non-null.
        """
        with connection.schema_editor() as editor:
            editor.create_model(AuthorWithDefaultHeight)
        old_field = AuthorWithDefaultHeight._meta.get_field('height')
        new_default = old_field.default * 2
        new_field = PositiveIntegerField(null=True, blank=True, default=new_default)
        new_field.set_attributes_from_name('height')
        with connection.schema_editor() as editor, self.assertNumQueries(0):
            editor.alter_field(AuthorWithDefaultHeight, old_field, new_field, strict=True)

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
        self.assertEqual(self.get_constraints_for_column(Author, 'weight'), ['schema_author_weight_587740f9'])

        # Remove db_index=True to drop index.
        with connection.schema_editor() as editor:
            editor.alter_field(Author, new_field, old_field, strict=True)
        self.assertEqual(self.get_constraints_for_column(Author, 'weight'), [])

    def test_alter_pk_with_self_referential_field(self):
        """
        Changing the primary key field name of a model with a self-referential
        foreign key (#26384).
        """
        with connection.schema_editor() as editor:
            editor.create_model(Node)
        old_field = Node._meta.get_field('node_id')
        new_field = AutoField(primary_key=True)
        new_field.set_attributes_from_name('id')
        with connection.schema_editor() as editor:
            editor.alter_field(Node, old_field, new_field, strict=True)
        self.assertForeignKeyExists(Node, 'parent_id', Node._meta.db_table)

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

    def test_namespaced_db_table_create_index_name(self):
        """
        Table names are stripped of their namespace/schema before being used to
        generate index names.
        """
        with connection.schema_editor() as editor:
            max_name_length = connection.ops.max_name_length() or 200
            namespace = 'n' * max_name_length
            table_name = 't' * max_name_length
            namespaced_table_name = '"%s"."%s"' % (namespace, table_name)
            self.assertEqual(
                editor._create_index_name(table_name, []),
                editor._create_index_name(namespaced_table_name, []),
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

    def test_rename_table_renames_deferred_sql_references(self):
        atomic_rename = connection.features.supports_atomic_references_rename
        with connection.schema_editor(atomic=atomic_rename) as editor:
            editor.create_model(Author)
            editor.create_model(Book)
            editor.alter_db_table(Author, 'schema_author', 'schema_renamed_author')
            editor.alter_db_table(Author, 'schema_book', 'schema_renamed_book')
            self.assertGreater(len(editor.deferred_sql), 0)
            for statement in editor.deferred_sql:
                self.assertIs(statement.references_table('schema_author'), False)
                self.assertIs(statement.references_table('schema_book'), False)

    @unittest.skipIf(connection.vendor == 'sqlite', 'SQLite naively remakes the table on field alteration.')
    def test_rename_column_renames_deferred_sql_references(self):
        with connection.schema_editor() as editor:
            editor.create_model(Author)
            editor.create_model(Book)
            old_title = Book._meta.get_field('title')
            new_title = CharField(max_length=100, db_index=True)
            new_title.set_attributes_from_name('renamed_title')
            editor.alter_field(Book, old_title, new_title)
            old_author = Book._meta.get_field('author')
            new_author = ForeignKey(Author, CASCADE)
            new_author.set_attributes_from_name('renamed_author')
            editor.alter_field(Book, old_author, new_author)
            self.assertGreater(len(editor.deferred_sql), 0)
            for statement in editor.deferred_sql:
                self.assertIs(statement.references_column('book', 'title'), False)
                self.assertIs(statement.references_column('book', 'author_id'), False)

    @isolate_apps('schema')
    def test_referenced_field_without_constraint_rename_inside_atomic_block(self):
        """
        Foreign keys without database level constraint don't prevent the field
        they reference from being renamed in an atomic block.
        """
        class Foo(Model):
            field = CharField(max_length=255, unique=True)

            class Meta:
                app_label = 'schema'

        class Bar(Model):
            foo = ForeignKey(Foo, CASCADE, to_field='field', db_constraint=False)

            class Meta:
                app_label = 'schema'

        self.isolated_local_models = [Foo, Bar]
        with connection.schema_editor() as editor:
            editor.create_model(Foo)
            editor.create_model(Bar)

        new_field = CharField(max_length=255, unique=True)
        new_field.set_attributes_from_name('renamed')
        with connection.schema_editor(atomic=True) as editor:
            editor.alter_field(Foo, Foo._meta.get_field('field'), new_field)

    @isolate_apps('schema')
    def test_referenced_table_without_constraint_rename_inside_atomic_block(self):
        """
        Foreign keys without database level constraint don't prevent the table
        they reference from being renamed in an atomic block.
        """
        class Foo(Model):
            field = CharField(max_length=255, unique=True)

            class Meta:
                app_label = 'schema'

        class Bar(Model):
            foo = ForeignKey(Foo, CASCADE, to_field='field', db_constraint=False)

            class Meta:
                app_label = 'schema'

        self.isolated_local_models = [Foo, Bar]
        with connection.schema_editor() as editor:
            editor.create_model(Foo)
            editor.create_model(Bar)

        new_field = CharField(max_length=255, unique=True)
        new_field.set_attributes_from_name('renamed')
        with connection.schema_editor(atomic=True) as editor:
            editor.alter_db_table(Foo, Foo._meta.db_table, 'renamed_table')
        Foo._meta.db_table = 'renamed_table'
