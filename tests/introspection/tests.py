from __future__ import unicode_literals

from django.db import connection
from django.test import TestCase, skipUnlessDBFeature

from .models import Reporter, Article


class IntrospectionTests(TestCase):
    def test_table_names(self):
        tl = connection.introspection.table_names()
        self.assertEqual(tl, sorted(tl))
        self.assertTrue(Reporter._meta.db_table in tl,
                     "'%s' isn't in table_list()." % Reporter._meta.db_table)
        self.assertTrue(Article._meta.db_table in tl,
                     "'%s' isn't in table_list()." % Article._meta.db_table)

    def test_django_table_names(self):
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE django_ixn_test_table (id INTEGER);')
            tl = connection.introspection.django_table_names()
            cursor.execute("DROP TABLE django_ixn_test_table;")
            self.assertTrue('django_ixn_testcase_table' not in tl,
                         "django_table_names() returned a non-Django table")

    def test_django_table_names_retval_type(self):
        # Ticket #15216
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE django_ixn_test_table (id INTEGER);')

        tl = connection.introspection.django_table_names(only_existing=True)
        self.assertIs(type(tl), list)

        tl = connection.introspection.django_table_names(only_existing=False)
        self.assertIs(type(tl), list)

    def test_installed_models(self):
        tables = [Article._meta.db_table, Reporter._meta.db_table]
        models = connection.introspection.installed_models(tables)
        self.assertEqual(models, set([Article, Reporter]))

    def test_sequence_list(self):
        sequences = connection.introspection.sequence_list()
        expected = {'table': Reporter._meta.db_table, 'column': 'id'}
        self.assertTrue(expected in sequences,
                     'Reporter sequence not found in sequence_list()')

    def test_get_table_description_names(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        self.assertEqual([r[0] for r in desc],
                         [f.column for f in Reporter._meta.fields])

    def test_get_table_description_types(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        self.assertEqual(
            [datatype(r[1], r) for r in desc],
            ['AutoField' if connection.features.can_introspect_autofield else 'IntegerField',
             'CharField', 'CharField', 'CharField',
             'BigIntegerField' if connection.features.can_introspect_big_integer_field else 'IntegerField',
             'BinaryField' if connection.features.can_introspect_binary_field else 'TextField']
        )

    # The following test fails on Oracle due to #17202 (can't correctly
    # inspect the length of character columns).
    @skipUnlessDBFeature('can_introspect_max_length')
    def test_get_table_description_col_lengths(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        self.assertEqual(
            [r[3] for r in desc if datatype(r[1], r) == 'CharField'],
            [30, 30, 75]
        )

    @skipUnlessDBFeature('can_introspect_null')
    def test_get_table_description_nullable(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        nullable_by_backend = connection.features.interprets_empty_strings_as_nulls
        self.assertEqual(
            [r[6] for r in desc],
            [False, nullable_by_backend, nullable_by_backend, nullable_by_backend, True, True]
        )

    # Regression test for #9991 - 'real' types in postgres
    @skipUnlessDBFeature('has_real_datatype')
    def test_postgresql_real_type(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE django_ixn_real_test_table (number REAL);")
            desc = connection.introspection.get_table_description(cursor, 'django_ixn_real_test_table')
            cursor.execute('DROP TABLE django_ixn_real_test_table;')
        self.assertEqual(datatype(desc[0][1], desc[0]), 'FloatField')

    def test_get_relations(self):
        with connection.cursor() as cursor:
            relations = connection.introspection.get_relations(cursor, Article._meta.db_table)

        # Older versions of MySQL don't have the chops to report on this stuff,
        # so just skip it if no relations come back. If they do, though, we
        # should test that the response is correct.
        if relations:
            # That's {field_index: (field_index_other_table, other_table)}
            self.assertEqual(relations, {3: (0, Reporter._meta.db_table),
                                         4: (0, Article._meta.db_table)})

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_get_key_columns(self):
        with connection.cursor() as cursor:
            key_columns = connection.introspection.get_key_columns(cursor, Article._meta.db_table)
        self.assertEqual(
            set(key_columns),
            set([('reporter_id', Reporter._meta.db_table, 'id'),
                 ('response_to_id', Article._meta.db_table, 'id')]))

    def test_get_primary_key_column(self):
        with connection.cursor() as cursor:
            primary_key_column = connection.introspection.get_primary_key_column(cursor, Article._meta.db_table)
        self.assertEqual(primary_key_column, 'id')

    def test_get_indexes(self):
        with connection.cursor() as cursor:
            indexes = connection.introspection.get_indexes(cursor, Article._meta.db_table)
        self.assertEqual(indexes['reporter_id'], {'unique': False, 'primary_key': False})

    def test_get_indexes_multicol(self):
        """
        Test that multicolumn indexes are not included in the introspection
        results.
        """
        with connection.cursor() as cursor:
            indexes = connection.introspection.get_indexes(cursor, Reporter._meta.db_table)
        self.assertNotIn('first_name', indexes)
        self.assertIn('id', indexes)


def datatype(dbtype, description):
    """Helper to convert a data type into a string."""
    dt = connection.introspection.get_field_type(dbtype, description)
    if type(dt) is tuple:
        return dt[0]
    else:
        return dt
