from django.contrib.gis.db.backends.postgis.indexes import GistIndex
from django.db import connection

from . import PostgisTestCase
from .models import IndexedCountry


class GistIndexTests(PostgisTestCase):

    def test_suffix(self):
        self.assertEqual(GistIndex.suffix, 'gist')

    def test_repr(self):
        index = GistIndex(fields=['mpoly'])
        self.assertEqual(repr(index), "<GistIndex: fields='mpoly'>")

    def test_eq(self):
        index = GistIndex(fields=['mpoly'])
        same_index = GistIndex(fields=['mpoly'])
        another_index = GistIndex(fields=['boundaries'])
        self.assertEqual(index, same_index)
        self.assertNotEqual(index, another_index)

    def test_name_auto_generation(self):
        index = GistIndex(fields=['mpoly'])
        index.set_name_with_model(IndexedCountry)
        self.assertEqual(index.name, 'geoapp_inde_mpoly_f6178a_gist')

    def test_deconstruction(self):
        index = GistIndex(fields=['mpoly'], name='test_mpoly_gist')
        path, args, kwargs = index.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.db.backends.postgis.indexes.GistIndex')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'fields': ['mpoly'], 'name': 'test_mpoly_gist'})


class SchemaTests(PostgisTestCase):

    def get_constraints(self, table):
        """
        Get the indexes on the table using a new cursor.
        """
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_gist_index(self):
        # Ensure the table is there and doesn't have an index.
        self.assertNotIn('mpoly', self.get_constraints(IndexedCountry._meta.db_table))
        # Add the index
        index_name = 'mpoly_model_field_gist'
        index = GistIndex(fields=['mpoly'], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(IndexedCountry, index)
        constraints = self.get_constraints(IndexedCountry._meta.db_table)
        # Check gist index was added
        self.assertEqual(constraints[index_name]['type'], GistIndex.suffix)
        # Drop the index
        with connection.schema_editor() as editor:
            editor.remove_index(IndexedCountry, index)
        self.assertNotIn(index_name, self.get_constraints(IndexedCountry._meta.db_table))

