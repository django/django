from unittest import skipUnless

from django.db import connection
from django.db.utils import DatabaseError
from django.test import TransactionTestCase, mock, skipUnlessDBFeature
from django.test.utils import ignore_warnings
from django.utils.deprecation import RemovedInDjango21Warning

from .models import Article, ArticleReporter, City, District, Reporter


class IntrospectionTests(TransactionTestCase):

    available_apps = ['introspection']

    def test_table_names(self):
        tl = connection.introspection.table_names()
        self.assertEqual(tl, sorted(tl))
        self.assertIn(Reporter._meta.db_table, tl, "'%s' isn't in table_list()." % Reporter._meta.db_table)
        self.assertIn(Article._meta.db_table, tl, "'%s' isn't in table_list()." % Article._meta.db_table)

    def test_django_table_names(self):
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE django_ixn_test_table (id INTEGER);')
            tl = connection.introspection.django_table_names()
            cursor.execute("DROP TABLE django_ixn_test_table;")
            self.assertNotIn('django_ixn_test_table', tl,
                             "django_table_names() returned a non-Django table")

    def test_django_table_names_retval_type(self):
        # Table name is a list #15216
        tl = connection.introspection.django_table_names(only_existing=True)
        self.assertIs(type(tl), list)
        tl = connection.introspection.django_table_names(only_existing=False)
        self.assertIs(type(tl), list)

    def test_table_names_with_views(self):
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    'CREATE VIEW introspection_article_view AS SELECT headline '
                    'from introspection_article;')
            except DatabaseError as e:
                if 'insufficient privileges' in str(e):
                    self.fail("The test user has no CREATE VIEW privileges")
                else:
                    raise

        self.assertIn('introspection_article_view', connection.introspection.table_names(include_views=True))
        self.assertNotIn('introspection_article_view', connection.introspection.table_names())

    def test_unmanaged_through_model(self):
        tables = connection.introspection.django_table_names()
        self.assertNotIn(ArticleReporter._meta.db_table, tables)

    def test_installed_models(self):
        tables = [Article._meta.db_table, Reporter._meta.db_table]
        models = connection.introspection.installed_models(tables)
        self.assertEqual(models, {Article, Reporter})

    def test_sequence_list(self):
        sequences = connection.introspection.sequence_list()
        expected = {'table': Reporter._meta.db_table, 'column': 'id'}
        self.assertIn(expected, sequences, 'Reporter sequence not found in sequence_list()')

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
             'BinaryField' if connection.features.can_introspect_binary_field else 'TextField',
             'SmallIntegerField' if connection.features.can_introspect_small_integer_field else 'IntegerField']
        )

    def test_get_table_description_col_lengths(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        self.assertEqual(
            [r[3] for r in desc if datatype(r[1], r) == 'CharField'],
            [30, 30, 254]
        )

    @skipUnlessDBFeature('can_introspect_null')
    def test_get_table_description_nullable(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        nullable_by_backend = connection.features.interprets_empty_strings_as_nulls
        self.assertEqual(
            [r[6] for r in desc],
            [False, nullable_by_backend, nullable_by_backend, nullable_by_backend, True, True, False]
        )

    @skipUnlessDBFeature('can_introspect_autofield')
    def test_bigautofield(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, City._meta.db_table)
        self.assertIn('BigAutoField', [datatype(r[1], r) for r in desc])

    # Regression test for #9991 - 'real' types in postgres
    @skipUnlessDBFeature('has_real_datatype')
    def test_postgresql_real_type(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE django_ixn_real_test_table (number REAL);")
            desc = connection.introspection.get_table_description(cursor, 'django_ixn_real_test_table')
            cursor.execute('DROP TABLE django_ixn_real_test_table;')
        self.assertEqual(datatype(desc[0][1], desc[0]), 'FloatField')

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_get_relations(self):
        with connection.cursor() as cursor:
            relations = connection.introspection.get_relations(cursor, Article._meta.db_table)

        # That's {field_name: (field_name_other_table, other_table)}
        expected_relations = {
            'reporter_id': ('id', Reporter._meta.db_table),
            'response_to_id': ('id', Article._meta.db_table),
        }
        self.assertEqual(relations, expected_relations)

        # Removing a field shouldn't disturb get_relations (#17785)
        body = Article._meta.get_field('body')
        with connection.schema_editor() as editor:
            editor.remove_field(Article, body)
        with connection.cursor() as cursor:
            relations = connection.introspection.get_relations(cursor, Article._meta.db_table)
        with connection.schema_editor() as editor:
            editor.add_field(Article, body)
        self.assertEqual(relations, expected_relations)

    @skipUnless(connection.vendor == 'sqlite', "This is an sqlite-specific issue")
    def test_get_relations_alt_format(self):
        """
        With SQLite, foreign keys can be added with different syntaxes and
        formatting.
        """
        create_table_statements = [
            "CREATE TABLE track(id, art_id INTEGER, FOREIGN KEY(art_id) REFERENCES {}(id));",
            "CREATE TABLE track(id, art_id INTEGER, FOREIGN KEY (art_id) REFERENCES {}(id));"
        ]
        for statement in create_table_statements:
            with connection.cursor() as cursor:
                cursor.fetchone = mock.Mock(return_value=[statement.format(Article._meta.db_table)])
                relations = connection.introspection.get_relations(cursor, 'mocked_table')
            self.assertEqual(relations, {'art_id': ('id', Article._meta.db_table)})

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_get_key_columns(self):
        with connection.cursor() as cursor:
            key_columns = connection.introspection.get_key_columns(cursor, Article._meta.db_table)
        self.assertEqual(
            set(key_columns),
            {('reporter_id', Reporter._meta.db_table, 'id'),
             ('response_to_id', Article._meta.db_table, 'id')})

    def test_get_primary_key_column(self):
        with connection.cursor() as cursor:
            primary_key_column = connection.introspection.get_primary_key_column(cursor, Article._meta.db_table)
            pk_fk_column = connection.introspection.get_primary_key_column(cursor, District._meta.db_table)
        self.assertEqual(primary_key_column, 'id')
        self.assertEqual(pk_fk_column, 'city_id')

    @ignore_warnings(category=RemovedInDjango21Warning)
    def test_get_indexes(self):
        with connection.cursor() as cursor:
            indexes = connection.introspection.get_indexes(cursor, Article._meta.db_table)
        self.assertEqual(indexes['reporter_id'], {'unique': False, 'primary_key': False})

    @ignore_warnings(category=RemovedInDjango21Warning)
    def test_get_indexes_multicol(self):
        """
        Multicolumn indexes are not included in the introspection results.
        """
        with connection.cursor() as cursor:
            indexes = connection.introspection.get_indexes(cursor, Reporter._meta.db_table)
        self.assertNotIn('first_name', indexes)
        self.assertIn('id', indexes)

    def test_get_constraints_index_types(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, Article._meta.db_table)
        index = {}
        for key, val in constraints.items():
            if val['columns'] == ['headline', 'pub_date']:
                index = val
        self.assertEqual(index['type'], 'btree')

    @skipUnlessDBFeature('supports_index_column_ordering')
    def test_get_constraints_indexes_orders(self):
        """
        Indexes have the 'orders' key with a list of 'ASC'/'DESC' values.
        """
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, Article._meta.db_table)
        indexes_verified = 0
        expected_columns = [
            ['reporter_id'],
            ['headline', 'pub_date'],
            ['response_to_id'],
        ]
        for key, val in constraints.items():
            if val['index'] and not (val['primary_key'] or val['unique']):
                self.assertIn(val['columns'], expected_columns)
                self.assertEqual(val['orders'], ['ASC'] * len(val['columns']))
                indexes_verified += 1
        self.assertEqual(indexes_verified, 3)


def datatype(dbtype, description):
    """Helper to convert a data type into a string."""
    dt = connection.introspection.get_field_type(dbtype, description)
    if type(dt) is tuple:
        return dt[0]
    else:
        return dt
