"""
Test PostgreSQL full text search vector field.
"""
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVectorField, WeightedColumn,
)
from django.db import connection, migrations, models
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter
from django.db.models.expressions import F
from . import PostgreSQLTestCase
from django.test.utils import isolate_apps


class SearchVectorFieldMigrationWriterTests(PostgreSQLTestCase):

    def test_deconstruct_no_columns(self):

        svf = SearchVectorField()

        self.assertEqual(
            ("django.contrib.postgres.search.SearchVectorField()",
             {'import django.contrib.postgres.search'}),
            MigrationWriter.serialize(svf)
        )

    def test_deconstruct(self):

        svf = SearchVectorField([
            WeightedColumn('name', 'A'),
            WeightedColumn('description', 'D'),
        ], 'english')

        self.assertEqual(
            ("django.contrib.postgres.search.SearchVectorField("
             "columns=["
             "django.contrib.postgres.search.WeightedColumn('name', 'A'), "
             "django.contrib.postgres.search.WeightedColumn('description', 'D')], "
             "language='english')",
             {'import django.contrib.postgres.search'}),
            MigrationWriter.serialize(svf)
        )


@isolate_apps('postgres_tests')
class SearchVectorFieldDDLTests(PostgreSQLTestCase):

    def test_sql_create_model_no_weightedcolumns(self):
        """
        If user does not provide 'columns' we still generate the index.
        Presumably, they will have to update the column themselves either in Python
        or via an unmanaged custom postgres trigger function.
        """

        class NoWeightedColumns(models.Model):
            search = SearchVectorField()

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(NoWeightedColumns)
            self.assertEqual(len(schema_editor.deferred_sql), 1)
            self.assertIn(
                'CREATE INDEX "postgres_tests_noweightedcolumns_search_7d3fd766"'
                ' ON "postgres_tests_noweightedcolumns" ("search")',
                schema_editor.deferred_sql[0]
            )

    def test_sql_create_model_with_weightedcolumns(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            body = models.TextField()
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
                WeightedColumn('body', 'D'),
            ], 'english')

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TextDocument)
            self.assertEqual(len(schema_editor.deferred_sql), 3)
            self.assertIn(
                'CREATE INDEX "postgres_tests_textdocument_search_9f678d09"'
                ' ON "postgres_tests_textdocument" ("search")',
                schema_editor.deferred_sql[0]
            )
            self.assertIn(
                'CREATE FUNCTION postgres_tests_textdocument_search_9f678d09_func() RETURNS trigger AS $$\n'
                'BEGIN\n'
                ' NEW."search" :=\n'
                '  setweight(to_tsvector(\'pg_catalog.english\', COALESCE(NEW."title", \'\')), \'A\') ||\n'
                '  setweight(to_tsvector(\'pg_catalog.english\', COALESCE(NEW."body", \'\')), \'D\') ;\n'
                ' RETURN NEW;\n'
                'END\n'
                '$$ LANGUAGE plpgsql',
                schema_editor.deferred_sql[1]
            )
            self.assertIn(
                'CREATE TRIGGER "postgres_tests_textdocument_search_9f678d09_trig" BEFORE INSERT OR UPDATE'
                ' ON "postgres_tests_textdocument" FOR EACH ROW'
                ' EXECUTE PROCEDURE postgres_tests_textdocument_search_9f678d09_func()',
                schema_editor.deferred_sql[2]
            )


@isolate_apps('postgres_tests', attr_name='apps')
class SearchVectorFieldMigrationTests(PostgreSQLTestCase):

    create_model = migrations.CreateModel(
        'textdocument', [
            ('title', models.CharField(max_length=128)),
            ('body', models.TextField()),
            ('search', SearchVectorField([WeightedColumn('body', 'A')], 'english')),
        ]
    )

    delete_model = migrations.DeleteModel('textdocument')

    create_model_without_search = migrations.CreateModel(
        'textdocument', [
            ('body', models.TextField()),
        ]
    )

    add_field = migrations.AddField(
        'textdocument', 'search',
        SearchVectorField([WeightedColumn('body', 'A')], 'english')
    )

    alter_field = migrations.AlterField(
        'textdocument', 'search',
        SearchVectorField([WeightedColumn('title', 'A'), WeightedColumn('body', 'D')], 'english')
    )

    remove_field = migrations.RemoveField(
        'textdocument', 'search'
    )

    def starting_state(self, operation):
        project_state = ProjectState.from_apps(self.apps)
        new_state = project_state.clone()
        with connection.schema_editor() as schema_editor:
            operation.state_forwards("postgres_tests", new_state)
            operation.database_forwards("postgres_tests", schema_editor, project_state, new_state)
            return new_state, new_state.clone()

    def test_create_model(self):

        project_state = ProjectState.from_apps(self.apps)
        new_state = project_state.clone()

        self.assertFITNotExists()

        with connection.schema_editor() as schema_editor:
            self.create_model.state_forwards("postgres_tests", new_state)
            self.create_model.database_forwards("postgres_tests", schema_editor, project_state, new_state)

        self.assertFITExists()

    def test_add_field(self):
        project_state, new_state = self.starting_state(self.create_model_without_search)

        self.assertFITNotExists()

        with connection.schema_editor() as schema_editor:
            self.add_field.state_forwards("postgres_tests", new_state)
            self.add_field.database_forwards("postgres_tests", schema_editor, project_state, new_state)

        self.assertFITExists()

    def test_remove_field(self):
        project_state, new_state = self.starting_state(self.create_model)

        self.assertFITExists()

        with connection.schema_editor() as schema_editor:
            self.remove_field.state_forwards("postgres_tests", new_state)
            self.remove_field.database_forwards("postgres_tests", schema_editor, project_state, new_state)

        self.assertFITNotExists()

    def test_alter_field(self):
        project_state, new_state = self.starting_state(self.create_model)

        self.assertFITExists()
        self.assertNotIn('title', self.get_function_src('search'))

        with connection.schema_editor() as schema_editor:
            self.alter_field.state_forwards("postgres_tests", new_state)
            self.alter_field.database_forwards("postgres_tests", schema_editor, project_state, new_state)

        self.assertFITExists()
        self.assertIn('title', self.get_function_src('search'))

    def test_delete_model(self):
        project_state, new_state = self.starting_state(self.create_model)

        self.assertFITExists()

        with connection.schema_editor() as schema_editor:
            self.delete_model.state_forwards("postgres_tests", new_state)
            self.delete_model.database_forwards("postgres_tests", schema_editor, project_state, new_state)

        self.assertFITNotExists()

    SEARCH_COL = 'postgres_tests_{table}_{column}_.{{8}}'
    FIT = [SEARCH_COL + '_func', SEARCH_COL, SEARCH_COL + '_trig']

    def assertFITExists(self, column='search', table='textdocument'):
        with_column = [fit.format(column=column, table=table) for fit in self.FIT]
        self.assertFunctionExists(with_column[0])
        self.assertIndexExists(with_column[1])
        self.assertTriggerExists(with_column[2])

    def assertFITNotExists(self, column='search', table='textdocument'):
        with_column = [fit.format(column=column, table=table) for fit in self.FIT]
        self.assertFunctionNotExists(with_column[0])
        self.assertIndexNotExists(with_column[1])
        self.assertTriggerNotExists(with_column[2])

    _sql_check_function = "select proname from pg_proc where proname ~ %s"

    def assertFunctionExists(self, name):
        return self.assertXExists(self._sql_check_function, name)

    def assertFunctionNotExists(self, name):
        return self.assertXNotExists(self._sql_check_function, name)

    _sql_check_trigger = "select tgname from pg_trigger where tgname ~ %s"

    def assertTriggerExists(self, name):
        return self.assertXExists(self._sql_check_trigger, name)

    def assertTriggerNotExists(self, name):
        return self.assertXNotExists(self._sql_check_trigger, name)

    _sql_check_index = "select indexname from pg_indexes where indexname ~ %s"

    def assertIndexExists(self, name):
        return self.assertXExists(self._sql_check_index, name)

    def assertIndexNotExists(self, name):
        return self.assertXNotExists(self._sql_check_index, name)

    def assertXExists(self, sql, x):
        self.assertTrue(self._does_x_exist(sql, x), x)

    def assertXNotExists(self, sql, x):
        self.assertFalse(self._does_x_exist(sql, x), x)

    def _does_x_exist(self, sql, x):
        with connection.cursor() as cursor:
            cursor.execute(sql, [x])
            return len(cursor.fetchall()) > 0

    def get_function_src(self, column='search', table='textdocument'):
        func = self.FIT[0].format(column=column, table=table)
        with connection.cursor() as cursor:
            cursor.execute("select prosrc from pg_proc where proname ~ %s", [func])
            return cursor.fetchone()[0]


@isolate_apps('postgres_tests')
class SearchVectorFieldQueryTests(PostgreSQLTestCase):

    def setUp(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            body = models.TextField()
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
                WeightedColumn('body', 'D'),
            ], 'english')

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TextDocument)

        TextDocument.objects.create(
            title="My hovercraft is full of eels.",
            body="Spam! Spam! Spam! Spam! Spam! Spam!",
        )
        TextDocument.objects.create(
            title="Spam! Spam! Spam! Spam! Spam! Spam!",
            body="My hovercraft is full of eels."
        )
        self.doc = TextDocument

    def search(self, terms):
        return list(self.doc.objects.filter(search=terms).values_list('id', flat=True))

    def test_search(self):
        self.assertEqual(self.search('hovercraft'), [1, 2])
        self.assertEqual(self.search('spam'), [1, 2])

    def ranked_search(self, terms):
        return list(self.doc.objects
                    .annotate(rank=SearchRank(F('search'), SearchQuery(terms, config='english')))
                    .order_by('-rank')
                    .values_list('id', flat=True))

    def test_rank_search(self):
        self.assertEqual(self.ranked_search('hovercraft'), [1, 2])
        self.assertEqual(self.ranked_search('spam'), [2, 1])
