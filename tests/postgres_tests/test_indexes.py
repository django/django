from django.contrib.postgres.indexes import GinIndex
from django.db import connection

from . import PostgreSQLTestCase
from .models import IntegerArrayModel


class GinIndexTests(PostgreSQLTestCase):

    def test_repr(self):
        index = GinIndex(fields=['title'])
        self.assertEqual(repr(index), "<GinIndex: fields='title'>")

    def test_eq(self):
        index = GinIndex(fields=['title'])
        same_index = GinIndex(fields=['title'])
        another_index = GinIndex(fields=['author'])
        self.assertEqual(index, same_index)
        self.assertNotEqual(index, another_index)

    def test_name_auto_generation(self):
        index = GinIndex(fields=['field'])
        index.set_name_with_model(IntegerArrayModel)
        self.assertEqual(index.name, 'postgres_te_field_def2f8_gin')

    def test_deconstruction(self):
        index = GinIndex(fields=['title'], name='test_title_gin')
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.indexes.GinIndex')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': ['title'], 'name': 'test_title_gin'})


class SchemaTests(PostgreSQLTestCase):

    def get_constraints(self, table):
        """
        Get the indexes on the table using a new cursor.
        """
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_gin_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn('field', self.get_constraints(IntegerArrayModel._meta.db_table))
        # Add the index
        index_name = 'integer_array_model_field_gin'
        index = GinIndex(fields=['field'], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(IntegerArrayModel, index)
        constraints = self.get_constraints(IntegerArrayModel._meta.db_table)
        # Check gin index was added
        self.assertEqual(constraints[index_name]['type'], 'gin')
        # Drop the index
        with connection.schema_editor() as editor:
            editor.remove_index(IntegerArrayModel, index)
        self.assertNotIn(index_name, self.get_constraints(IntegerArrayModel._meta.db_table))
