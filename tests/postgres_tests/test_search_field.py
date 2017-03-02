"""
Test PostgreSQL full text search vector field.
"""
from datetime import datetime

from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVectorField, WeightedColumn,
)
from django.db import connection, migrations, models
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter
from django.db.models.expressions import F
from django.test.utils import isolate_apps

from . import PostgreSQLTestCase
from .test_search import VERSES


@isolate_apps('postgres_tests')
class CheckTests(PostgreSQLTestCase):

    def test_without_arguments(self):

        class TextDocument(models.Model):
            search = SearchVectorField()

        errors = TextDocument.check()
        self.assertEqual(len(errors), 0)

    def test_good_arguments(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            title2 = models.CharField(max_length=128, db_column='body')
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
                WeightedColumn('body', 'D')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 0)

    def test_columns_E100(self):

        class TextDocument(models.Model):
            search = SearchVectorField([
                WeightedColumn('title', 'A')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E100')
        self.assertIn('No textual columns', errors[0].msg)

    def test_columns_E101(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                ('title', 'A')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E101')
        self.assertIn('columns', errors[0].msg)
        self.assertIn('iterable', errors[0].msg)
        self.assertIn('WeightedColumn', errors[0].msg)

    def test_languages_required_E102(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('title', 'A')
            ])

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E102')
        self.assertIn('required', errors[0].msg)
        self.assertIn('language', errors[0].msg)
        self.assertIn('language_column', errors[0].msg)

    def test_language_E103(self):

        class TextDocument(models.Model):
            search = SearchVectorField(language=1)

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E103')
        self.assertIn('language', errors[0].msg)

    def test_language_column_E104(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField(language_column='body')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E104')
        self.assertIn('language_column', errors[0].msg)
        self.assertIn('title', errors[0].msg)

    def test_force_update_E105(self):

        class TextDocument(models.Model):
            search = SearchVectorField(force_update='invalid')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E105')
        self.assertIn('force_update', errors[0].msg)
        self.assertIn('True or False', errors[0].msg)

    def test_WeightedColumn_name_E110(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('body', 'A')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E110')
        self.assertIn('body', errors[0].msg)
        self.assertIn('available columns', errors[0].msg)
        self.assertIn('title', errors[0].msg)

    def test_WeightedColumn_weight_E111(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('title', 'X')
            ], language='english')

        errors = TextDocument.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E111')
        self.assertIn('weight', errors[0].msg)
        self.assertIn('"A", "B", "C"', errors[0].msg)

    def test_several_errors(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('body', 'A'),
                WeightedColumn('name', 'X')
            ], language=9, force_update=False)

        errors = TextDocument.check()
        self.assertEqual(len(errors), 4)


class MigrationWriterTests(PostgreSQLTestCase):

    def test_deconstruct_with_no_arguments(self):
        svf = SearchVectorField()
        self.assertEqual(
            ("django.contrib.postgres.search.SearchVectorField()",
             {'import django.contrib.postgres.search'}),
            MigrationWriter.serialize(svf)
        )

    def test_deconstruct_default_arguments(self):

        svf = SearchVectorField([
            WeightedColumn('name', 'A'),
            WeightedColumn('description', 'D'),
        ], language=None, language_column=None, force_update=False)

        definition, path = MigrationWriter.serialize(svf)

        self.assertEqual(
            "django.contrib.postgres.search.SearchVectorField("
            "columns=["
            "django.contrib.postgres.search.WeightedColumn('name', 'A'), "
            "django.contrib.postgres.search.WeightedColumn('description', 'D')]"
            ")",
            definition
        )

        self.assertSetEqual(
            {'import django.contrib.postgres.search'},
            path
        )

    def test_deconstruct_all_arguments(self):

        class TextDocument(models.Model):
            svf = SearchVectorField([
                WeightedColumn('name', 'A'),
                WeightedColumn('description', 'D'),
            ], language='english', language_column='lang', force_update=True)

        name, path, args, kwargs = TextDocument._meta.get_field('svf').deconstruct()

        self.assertEqual(name, "svf")
        self.assertEqual(path, "django.contrib.postgres.search.SearchVectorField")
        self.assertFalse(args)
        self.assertSetEqual(set(kwargs.keys()), {
            'columns', 'language', 'language_column', 'force_update'
        })


@isolate_apps('postgres_tests')
class SchemaEditorTests(PostgreSQLTestCase):

    def test_sql_setweight(self):

        def check_sql(model, sql):
            with connection.schema_editor() as schema_editor:
                field = model._meta.get_field('search')
                self.assertEqual(
                    sql, schema_editor._tsvector_setweight(field)
                )

        class WithLanguageTwoColumn(models.Model):
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
                WeightedColumn('body', 'D'),
            ], language='ukrainian')

        class WithLanguage(models.Model):
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], language='ukrainian')

        class WithLanguageColumn(models.Model):
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], language_column='lang')

        class WithLanguageAndLanguageColumn(models.Model):
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], language='ukrainian', language_column='lang')

        check_sql(
            WithLanguageTwoColumn, [
                """setweight(to_tsvector('ukrainian', COALESCE(NEW."title", '')), 'A') ||""",
                """setweight(to_tsvector('ukrainian', COALESCE(NEW."body", '')), 'D');"""
            ]
        )

        check_sql(
            WithLanguage, [
                """setweight(to_tsvector('ukrainian', COALESCE(NEW."body", '')), 'D');"""
            ]
        )

        check_sql(
            WithLanguageColumn, [
                """setweight(to_tsvector(NEW."lang"::regconfig, COALESCE(NEW."body", '')), 'D');"""
            ]
        )

        check_sql(
            WithLanguageAndLanguageColumn, [
                """setweight(to_tsvector(COALESCE(NEW."lang"::regconfig, 'ukrainian'),"""
                """ COALESCE(NEW."body", '')), 'D');"""
            ]
        )

    def test_sql_update_column_checks(self):

        def check_sql(model, sql):
            with connection.schema_editor() as schema_editor:
                field = model._meta.get_field('search')
                self.assertEqual(
                    sql, schema_editor._tsvector_update_column_checks(field)
                )

        class OneColumn(models.Model):
            search = SearchVectorField([
                WeightedColumn('name', 'A'),
            ])

        class ThreeColumns(models.Model):
            search = SearchVectorField([
                WeightedColumn('name', 'A'),
                WeightedColumn('title', 'B'),
                WeightedColumn('body', 'C'),
            ])

        check_sql(
            OneColumn, [
                'IF (NEW."name" <> OLD."name") THEN do_update = true;',
                'END IF;'
            ]
        )

        check_sql(
            ThreeColumns, [
                'IF (NEW."name" <> OLD."name") THEN do_update = true;',
                'ELSIF (NEW."title" <> OLD."title") THEN do_update = true;',
                'ELSIF (NEW."body" <> OLD."body") THEN do_update = true;',
                'END IF;'
            ]
        )

    def test_sql_update_function(self):

        def check_sql(model, sql):
            with connection.schema_editor() as schema_editor:
                field = model._meta.get_field('search')
                self.assertEqual(
                    sql, schema_editor._create_tsvector_update_function('thefunction', field)
                )

        class TextDocument(models.Model):
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
                WeightedColumn('body', 'D'),
            ], 'english')

        check_sql(
            TextDocument,
            "CREATE FUNCTION thefunction() RETURNS trigger AS $$\n"
            "DECLARE\n"
            " do_update bool default false;\n"
            "BEGIN\n"
            " IF (TG_OP = 'INSERT') THEN do_update = true;\n"
            " ELSIF (TG_OP = 'UPDATE') THEN\n"
            '  IF (NEW."title" <> OLD."title") THEN do_update = true;\n'
            '  ELSIF (NEW."body" <> OLD."body") THEN do_update = true;\n'
            "  END IF;\n"
            " END IF;\n"
            " IF do_update THEN\n"
            '  NEW."search" :=\n'
            "   setweight(to_tsvector('english', COALESCE(NEW.\"title\", '')), 'A') ||\n"
            "   setweight(to_tsvector('english', COALESCE(NEW.\"body\", '')), 'D');\n"
            " END IF;\n"
            " RETURN NEW;\n"
            "END\n"
            "$$ LANGUAGE plpgsql"
        )

        class TextDocumentForceUpdate(models.Model):
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], 'english', force_update=True)

        check_sql(
            TextDocumentForceUpdate,
            "CREATE FUNCTION thefunction() RETURNS trigger AS $$\n"
            "DECLARE\n"
            " do_update bool default false;\n"
            "BEGIN\n"
            " do_update = true;\n"
            " IF do_update THEN\n"
            '  NEW."search" :=\n'
            "   setweight(to_tsvector('english', COALESCE(NEW.\"body\", '')), 'D');\n"
            " END IF;\n"
            " RETURN NEW;\n"
            "END\n"
            "$$ LANGUAGE plpgsql"
        )

    def test_create_model_no_function(self):

        class NoWeightedColumns(models.Model):
            search = SearchVectorField()

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(NoWeightedColumns)
            self.assertEqual(len(schema_editor.deferred_sql), 1)
            self.assertIn('CREATE INDEX', schema_editor.deferred_sql[0])

    def test_create_model(self):

        class TextDocument(models.Model):
            title = models.CharField(max_length=128)
            search = SearchVectorField([
                WeightedColumn('title', 'A'),
            ], 'english')

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TextDocument)
            self.assertEqual(len(schema_editor.deferred_sql), 3)
            self.assertIn('CREATE INDEX', schema_editor.deferred_sql[0])
            self.assertIn('CREATE FUNCTION', schema_editor.deferred_sql[1])
            self.assertIn('CREATE TRIGGER', schema_editor.deferred_sql[2])


@isolate_apps('postgres_tests', attr_name='apps')
class MigrationTests(PostgreSQLTestCase):

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
class TriggerTests(PostgreSQLTestCase):

    def setUp(self):

        class TextDocument(models.Model):
            body = models.TextField()
            other = models.TextField()
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], 'english')

        class TextDocumentLanguageColumn(models.Model):
            body = models.TextField()
            lang = models.TextField(null=True)
            search = SearchVectorField([
                WeightedColumn('body', 'D'),
            ], language_column='lang', language='english')

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TextDocument)
            schema_editor.create_model(TextDocumentLanguageColumn)

        self.create = TextDocument.objects.create
        self.lang = TextDocumentLanguageColumn.objects.create

    def test_insert_and_update(self):
        doc = self.create(body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2")

        doc.body = 'No hovercraft for you!'
        doc.save()
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'hovercraft':2")

    def test_performance_improvement_for_guarded_update(self):

        text = '\n'.join(VERSES * 20)
        text2 = text.replace('brave', 'wimpy')

        start = datetime.now()
        doc = self.create(body=text)
        create_elapsed = (datetime.now() - start).microseconds
        doc.refresh_from_db()

        doc.body = text2
        start = datetime.now()
        doc.save(update_fields=['body'])
        update_elapsed = (datetime.now() - start).microseconds
        doc.refresh_from_db()

        longest = max(create_elapsed, update_elapsed)

        # check that insert and update times are within 50% of each other
        percent = abs(create_elapsed - update_elapsed) / longest
        self.assertGreater(.5, percent)

        # update not indexed column
        doc.other = text2
        start = datetime.now()
        doc.save(update_fields=['other'])
        noindex_elapsed = (datetime.now() - start).microseconds

        # skipping unnecessary to_tsvector() call is faster
        self.assertGreater(longest, noindex_elapsed)

        # update indexed column with the same value
        doc.body = text2
        start = datetime.now()
        doc.save(update_fields=['body'])
        noindex_elapsed = (datetime.now() - start).microseconds

        # skipping unnecessary to_tsvector() call is faster
        self.assertGreater(longest, noindex_elapsed)

    def test_using_language_column(self):
        # use english config to parse english text, stop words removed
        doc = self.lang(lang='english', body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2")

        # use german config to parse english text, stop words not removed
        doc = self.lang(lang='german', body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2 'is':3 'my':1 'of':5")

        # use english backup config to parse english text, stop words removed
        doc = self.lang(lang=None, body="My hovercraft is full of eels.")
        doc.refresh_from_db()
        self.assertEqual(doc.search, "'eel':6 'full':4 'hovercraft':2")


@isolate_apps('postgres_tests')
class QueryTests(PostgreSQLTestCase):

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
