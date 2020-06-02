from unittest import skipUnless

from django.db import connection
from django.db.models import Index
from django.test import TransactionTestCase

from ..utils import mysql, oracle, postgis
from .models import City


class SchemaIndexesTests(TransactionTestCase):
    available_apps = []
    models = [City]

    def get_indexes(self, table):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, table)
            return {
                name: constraint['columns']
                for name, constraint in constraints.items()
                if constraint['index']
            }

    def has_spatial_indexes(self, table):
        if mysql:
            with connection.cursor() as cursor:
                return connection.introspection.supports_spatial_index(cursor, table)
        elif oracle:
            # Spatial indexes in Meta.indexes are not supported by the Oracle
            # backend (see #31252).
            return False
        return True

    @skipUnless(postgis, 'This is a PostGIS-specific test.')
    def test_using_sql(self):
        index = Index(fields=['point'])
        editor = connection.schema_editor()
        self.assertIn(
            '%s USING ' % editor.quote_name(City._meta.db_table),
            str(index.create_sql(City, editor)),
        )

    def test_index_name(self):
        if not self.has_spatial_indexes(City._meta.db_table):
            self.skipTest('Spatial indexes in Meta.indexes are not supported.')
        index_name = 'custom_point_index_name'
        index = Index(fields=['point'], name=index_name)
        with connection.schema_editor() as editor:
            editor.add_index(City, index)
            indexes = self.get_indexes(City._meta.db_table)
            self.assertIn(index_name, indexes)
            self.assertEqual(indexes[index_name], ['point'])
            editor.remove_index(City, index)
