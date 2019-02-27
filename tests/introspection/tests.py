from unittest import mock, skipUnless

from django.db import connection
from django.db.models import Index
from django.db.utils import DatabaseError
from django.test import TransactionTestCase, skipUnlessDBFeature

from .models import Article, ArticleReporter, City, Comment, District, Reporter


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
        try:
            self.assertIn('introspection_article_view', connection.introspection.table_names(include_views=True))
            self.assertNotIn('introspection_article_view', connection.introspection.table_names())
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP VIEW introspection_article_view')

    def test_unmanaged_through_model(self):
        tables = connection.introspection.django_table_names()
        self.assertNotIn(ArticleReporter._meta.db_table, tables)

    def test_installed_models(self):
        tables = [Article._meta.db_table, Reporter._meta.db_table]
        models = connection.introspection.installed_models(tables)
        self.assertEqual(models, {Article, Reporter})

    def test_sequence_list(self):
        sequences = connection.introspection.sequence_list()
        reporter_seqs = [seq for seq in sequences if seq['table'] == Reporter._meta.db_table]
        self.assertEqual(len(reporter_seqs), 1, 'Reporter sequence not found in sequence_list()')
        self.assertEqual(reporter_seqs[0]['column'], 'id')

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
            [
                'AutoField' if connection.features.can_introspect_autofield else 'IntegerField',
                'CharField',
                'CharField',
                'CharField',
                'BigIntegerField' if connection.features.can_introspect_big_integer_field else 'IntegerField',
                'BinaryField' if connection.features.can_introspect_binary_field else 'TextField',
                'SmallIntegerField' if connection.features.can_introspect_small_integer_field else 'IntegerField',
                'DurationField' if connection.features.can_introspect_duration_field else 'BigIntegerField',
            ]
        )

    def test_get_table_description_col_lengths(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        self.assertEqual(
            [r[3] for r in desc if datatype(r[1], r) == 'CharField'],
            [30, 30, 254]
        )

    def test_get_table_description_nullable(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        nullable_by_backend = connection.features.interprets_empty_strings_as_nulls
        self.assertEqual(
            [r[6] for r in desc],
            [False, nullable_by_backend, nullable_by_backend, nullable_by_backend, True, True, False, False]
        )

    @skipUnlessDBFeature('can_introspect_autofield')
    def test_bigautofield(self):
        with connection.cursor() as cursor:
            desc = connection.introspection.get_table_description(cursor, City._meta.db_table)
        self.assertIn(connection.features.introspected_big_auto_field_type, [datatype(r[1], r) for r in desc])

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
                cursor.fetchone = mock.Mock(return_value=[statement.format(Article._meta.db_table), 'table'])
                relations = connection.introspection.get_relations(cursor, 'mocked_table')
            self.assertEqual(relations, {'art_id': ('id', Article._meta.db_table)})

    @skipUnlessDBFeature('can_introspect_foreign_keys')
    def test_get_key_columns(self):
        with connection.cursor() as cursor:
            key_columns = connection.introspection.get_key_columns(cursor, Article._meta.db_table)
        self.assertEqual(set(key_columns), {
            ('reporter_id', Reporter._meta.db_table, 'id'),
            ('response_to_id', Article._meta.db_table, 'id'),
        })

    def test_get_primary_key_column(self):
        with connection.cursor() as cursor:
            primary_key_column = connection.introspection.get_primary_key_column(cursor, Article._meta.db_table)
            pk_fk_column = connection.introspection.get_primary_key_column(cursor, District._meta.db_table)
        self.assertEqual(primary_key_column, 'id')
        self.assertEqual(pk_fk_column, 'city_id')

    def test_get_constraints_index_types(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, Article._meta.db_table)
        index = {}
        index2 = {}
        for val in constraints.values():
            if val['columns'] == ['headline', 'pub_date']:
                index = val
            if val['columns'] == ['headline', 'response_to_id', 'pub_date', 'reporter_id']:
                index2 = val
        self.assertEqual(index['type'], Index.suffix)
        self.assertEqual(index2['type'], Index.suffix)

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
            ['headline', 'response_to_id', 'pub_date', 'reporter_id'],
        ]
        for val in constraints.values():
            if val['index'] and not (val['primary_key'] or val['unique']):
                self.assertIn(val['columns'], expected_columns)
                self.assertEqual(val['orders'], ['ASC'] * len(val['columns']))
                indexes_verified += 1
        self.assertEqual(indexes_verified, 4)

    def test_get_constraints(self):
        def assertDetails(details, cols, primary_key=False, unique=False, index=False, check=False, foreign_key=None):
            # Different backends have different values for same constraints:
            #               PRIMARY KEY     UNIQUE CONSTRAINT    UNIQUE INDEX
            # MySQL      pk=1 uniq=1 idx=1  pk=0 uniq=1 idx=1  pk=0 uniq=1 idx=1
            # PostgreSQL pk=1 uniq=1 idx=0  pk=0 uniq=1 idx=0  pk=0 uniq=1 idx=1
            # SQLite     pk=1 uniq=0 idx=0  pk=0 uniq=1 idx=0  pk=0 uniq=1 idx=1
            if details['primary_key']:
                details['unique'] = True
            if details['unique']:
                details['index'] = False
            self.assertEqual(details['columns'], cols)
            self.assertEqual(details['primary_key'], primary_key)
            self.assertEqual(details['unique'], unique)
            self.assertEqual(details['index'], index)
            self.assertEqual(details['check'], check)
            self.assertEqual(details['foreign_key'], foreign_key)

        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, Comment._meta.db_table)
        # Test custom constraints
        custom_constraints = {
            'article_email_pub_date_uniq',
            'email_pub_date_idx',
        }
        if connection.features.supports_column_check_constraints:
            custom_constraints.add('up_votes_gte_0_check')
            assertDetails(constraints['up_votes_gte_0_check'], ['up_votes'], check=True)
        assertDetails(constraints['article_email_pub_date_uniq'], ['article_id', 'email', 'pub_date'], unique=True)
        assertDetails(constraints['email_pub_date_idx'], ['email', 'pub_date'], index=True)
        # Test field constraints
        field_constraints = set()
        for name, details in constraints.items():
            if name in custom_constraints:
                continue
            elif details['columns'] == ['up_votes'] and details['check']:
                assertDetails(details, ['up_votes'], check=True)
                field_constraints.add(name)
            elif details['columns'] == ['ref'] and details['unique']:
                assertDetails(details, ['ref'], unique=True)
                field_constraints.add(name)
            elif details['columns'] == ['article_id'] and details['index']:
                assertDetails(details, ['article_id'], index=True)
                field_constraints.add(name)
            elif details['columns'] == ['id'] and details['primary_key']:
                assertDetails(details, ['id'], primary_key=True, unique=True)
                field_constraints.add(name)
            elif details['columns'] == ['article_id'] and details['foreign_key']:
                assertDetails(details, ['article_id'], foreign_key=('introspection_article', 'id'))
                field_constraints.add(name)
            elif details['check']:
                # Some databases (e.g. Oracle) include additional check
                # constraints.
                field_constraints.add(name)
        # All constraints are accounted for.
        self.assertEqual(constraints.keys() ^ (custom_constraints | field_constraints), set())


def datatype(dbtype, description):
    """Helper to convert a data type into a string."""
    dt = connection.introspection.get_field_type(dbtype, description)
    if type(dt) is tuple:
        return dt[0]
    else:
        return dt
