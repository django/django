import datetime
from unittest import skipIf, skipUnless

from django.db import connection
from django.db.models import CASCADE, ForeignKey, Index, Q
from django.test import (
    TestCase, TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature,
)
from django.test.utils import override_settings
from django.utils import timezone

from .models import (
    Article, ArticleTranslation, IndexedArticle2, IndexTogetherSingleList,
)


class SchemaIndexesTests(TestCase):
    """
    Test index handling by the db.backends.schema infrastructure.
    """

    def test_index_name_hash(self):
        """
        Index names should be deterministic.
        """
        editor = connection.schema_editor()
        index_name = editor._create_index_name(
            table_name=Article._meta.db_table,
            column_names=("c1",),
            suffix="123",
        )
        self.assertEqual(index_name, "indexes_article_c1_a52bd80b123")

    def test_index_name(self):
        """
        Index names on the built-in database backends::
            * Are truncated as needed.
            * Include all the column names.
            * Include a deterministic hash.
        """
        long_name = 'l%sng' % ('o' * 100)
        editor = connection.schema_editor()
        index_name = editor._create_index_name(
            table_name=Article._meta.db_table,
            column_names=('c1', 'c2', long_name),
            suffix='ix',
        )
        expected = {
            'mysql': 'indexes_article_c1_c2_looooooooooooooooooo_255179b2ix',
            'oracle': 'indexes_a_c1_c2_loo_255179b2ix',
            'postgresql': 'indexes_article_c1_c2_loooooooooooooooooo_255179b2ix',
            'sqlite': 'indexes_article_c1_c2_l%sng_255179b2ix' % ('o' * 100),
        }
        if connection.vendor not in expected:
            self.skipTest('This test is only supported on the built-in database backends.')
        self.assertEqual(index_name, expected[connection.vendor])

    def test_index_together(self):
        editor = connection.schema_editor()
        index_sql = [str(statement) for statement in editor._model_indexes_sql(Article)]
        self.assertEqual(len(index_sql), 1)
        # Ensure the index name is properly quoted
        self.assertIn(
            connection.ops.quote_name(
                editor._create_index_name(Article._meta.db_table, ['headline', 'pub_date'], suffix='_idx')
            ),
            index_sql[0]
        )

    def test_index_together_single_list(self):
        # Test for using index_together with a single list (#22172)
        index_sql = connection.schema_editor()._model_indexes_sql(IndexTogetherSingleList)
        self.assertEqual(len(index_sql), 1)

    def test_columns_list_sql(self):
        index = Index(fields=['headline'], name='whitespace_idx')
        editor = connection.schema_editor()
        self.assertIn(
            '(%s)' % editor.quote_name('headline'),
            str(index.create_sql(Article, editor)),
        )

    def test_descending_columns_list_sql(self):
        index = Index(fields=['-headline'], name='whitespace_idx')
        editor = connection.schema_editor()
        self.assertIn(
            '(%s DESC)' % editor.quote_name('headline'),
            str(index.create_sql(Article, editor)),
        )


@skipIf(connection.vendor == 'postgresql', 'opclasses are PostgreSQL only')
class SchemaIndexesNotPostgreSQLTests(TransactionTestCase):
    available_apps = ['indexes']

    def test_create_index_ignores_opclasses(self):
        index = Index(
            name='test_ops_class',
            fields=['headline'],
            opclasses=['varchar_pattern_ops'],
        )
        with connection.schema_editor() as editor:
            # This would error if opclasses weren't ignored.
            editor.add_index(IndexedArticle2, index)


# The `condition` parameter is ignored by databases that don't support partial
# indexes.
@skipIfDBFeature('supports_partial_indexes')
class PartialIndexConditionIgnoredTests(TransactionTestCase):
    available_apps = ['indexes']

    def test_condition_ignored(self):
        index = Index(
            name='test_condition_ignored',
            fields=['published'],
            condition=Q(published=True),
        )
        with connection.schema_editor() as editor:
            # This would error if condition weren't ignored.
            editor.add_index(Article, index)

        self.assertNotIn(
            'WHERE %s' % editor.quote_name('published'),
            str(index.create_sql(Article, editor))
        )


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL tests')
class SchemaIndexesPostgreSQLTests(TransactionTestCase):
    available_apps = ['indexes']
    get_opclass_query = '''
        SELECT opcname, c.relname FROM pg_opclass AS oc
        JOIN pg_index as i on oc.oid = ANY(i.indclass)
        JOIN pg_class as c on c.oid = i.indexrelid
        WHERE c.relname = '%s'
    '''

    def test_text_indexes(self):
        """Test creation of PostgreSQL-specific text indexes (#12234)"""
        from .models import IndexedArticle
        index_sql = [str(statement) for statement in connection.schema_editor()._model_indexes_sql(IndexedArticle)]
        self.assertEqual(len(index_sql), 5)
        self.assertIn('("headline" varchar_pattern_ops)', index_sql[1])
        self.assertIn('("body" text_pattern_ops)', index_sql[3])
        # unique=True and db_index=True should only create the varchar-specific
        # index (#19441).
        self.assertIn('("slug" varchar_pattern_ops)', index_sql[4])

    def test_virtual_relation_indexes(self):
        """Test indexes are not created for related objects"""
        index_sql = connection.schema_editor()._model_indexes_sql(Article)
        self.assertEqual(len(index_sql), 1)

    def test_ops_class(self):
        index = Index(
            name='test_ops_class',
            fields=['headline'],
            opclasses=['varchar_pattern_ops'],
        )
        with connection.schema_editor() as editor:
            editor.add_index(IndexedArticle2, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query % 'test_ops_class')
            self.assertEqual(cursor.fetchall(), [('varchar_pattern_ops', 'test_ops_class')])

    def test_ops_class_multiple_columns(self):
        index = Index(
            name='test_ops_class_multiple',
            fields=['headline', 'body'],
            opclasses=['varchar_pattern_ops', 'text_pattern_ops'],
        )
        with connection.schema_editor() as editor:
            editor.add_index(IndexedArticle2, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query % 'test_ops_class_multiple')
            expected_ops_classes = (
                ('varchar_pattern_ops', 'test_ops_class_multiple'),
                ('text_pattern_ops', 'test_ops_class_multiple'),
            )
            self.assertCountEqual(cursor.fetchall(), expected_ops_classes)

    def test_ops_class_partial(self):
        index = Index(
            name='test_ops_class_partial',
            fields=['body'],
            opclasses=['text_pattern_ops'],
            condition=Q(headline__contains='China'),
        )
        with connection.schema_editor() as editor:
            editor.add_index(IndexedArticle2, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query % 'test_ops_class_partial')
            self.assertCountEqual(cursor.fetchall(), [('text_pattern_ops', 'test_ops_class_partial')])

    def test_ops_class_partial_tablespace(self):
        indexname = 'test_ops_class_tblspace'
        index = Index(
            name=indexname,
            fields=['body'],
            opclasses=['text_pattern_ops'],
            condition=Q(headline__contains='China'),
            db_tablespace='pg_default',
        )
        with connection.schema_editor() as editor:
            editor.add_index(IndexedArticle2, index)
            self.assertIn('TABLESPACE "pg_default" ', str(index.create_sql(IndexedArticle2, editor)))
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query % indexname)
            self.assertCountEqual(cursor.fetchall(), [('text_pattern_ops', indexname)])

    def test_ops_class_descending(self):
        indexname = 'test_ops_class_ordered'
        index = Index(
            name=indexname,
            fields=['-body'],
            opclasses=['text_pattern_ops'],
        )
        with connection.schema_editor() as editor:
            editor.add_index(IndexedArticle2, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query % indexname)
            self.assertCountEqual(cursor.fetchall(), [('text_pattern_ops', indexname)])

    def test_ops_class_descending_partial(self):
        indexname = 'test_ops_class_ordered_partial'
        index = Index(
            name=indexname,
            fields=['-body'],
            opclasses=['text_pattern_ops'],
            condition=Q(headline__contains='China'),
        )
        with connection.schema_editor() as editor:
            editor.add_index(IndexedArticle2, index)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query % indexname)
            self.assertCountEqual(cursor.fetchall(), [('text_pattern_ops', indexname)])

    def test_ops_class_columns_lists_sql(self):
        index = Index(
            fields=['headline'],
            name='whitespace_idx',
            opclasses=['text_pattern_ops'],
        )
        with connection.schema_editor() as editor:
            self.assertIn(
                '(%s text_pattern_ops)' % editor.quote_name('headline'),
                str(index.create_sql(Article, editor)),
            )

    def test_ops_class_descending_columns_list_sql(self):
        index = Index(
            fields=['-headline'],
            name='whitespace_idx',
            opclasses=['text_pattern_ops'],
        )
        with connection.schema_editor() as editor:
            self.assertIn(
                '(%s text_pattern_ops DESC)' % editor.quote_name('headline'),
                str(index.create_sql(Article, editor)),
            )


@skipUnless(connection.vendor == 'mysql', 'MySQL tests')
class SchemaIndexesMySQLTests(TransactionTestCase):
    available_apps = ['indexes']

    def test_no_index_for_foreignkey(self):
        """
        MySQL on InnoDB already creates indexes automatically for foreign keys.
        (#14180). An index should be created if db_constraint=False (#26171).
        """
        storage = connection.introspection.get_storage_engine(
            connection.cursor(), ArticleTranslation._meta.db_table
        )
        if storage != "InnoDB":
            self.skip("This test only applies to the InnoDB storage engine")
        index_sql = [str(statement) for statement in connection.schema_editor()._model_indexes_sql(ArticleTranslation)]
        self.assertEqual(index_sql, [
            'CREATE INDEX `indexes_articletranslation_article_no_constraint_id_d6c0806b` '
            'ON `indexes_articletranslation` (`article_no_constraint_id`)'
        ])

        # The index also shouldn't be created if the ForeignKey is added after
        # the model was created.
        field_created = False
        try:
            with connection.schema_editor() as editor:
                new_field = ForeignKey(Article, CASCADE)
                new_field.set_attributes_from_name('new_foreign_key')
                editor.add_field(ArticleTranslation, new_field)
                field_created = True
                # No deferred SQL. The FK constraint is included in the
                # statement to add the field.
                self.assertFalse(editor.deferred_sql)
        finally:
            if field_created:
                with connection.schema_editor() as editor:
                    editor.remove_field(ArticleTranslation, new_field)


@skipUnlessDBFeature('supports_partial_indexes')
# SQLite doesn't support timezone-aware datetimes when USE_TZ is False.
@override_settings(USE_TZ=True)
class PartialIndexTests(TransactionTestCase):
    # Schema editor is used to create the index to test that it works.
    available_apps = ['indexes']

    def test_partial_index(self):
        with connection.schema_editor() as editor:
            index = Index(
                name='recent_article_idx',
                fields=['pub_date'],
                condition=Q(
                    pub_date__gt=datetime.datetime(
                        year=2015, month=1, day=1,
                        # PostgreSQL would otherwise complain about the lookup
                        # being converted to a mutable function (by removing
                        # the timezone in the cast) which is forbidden.
                        tzinfo=timezone.get_current_timezone(),
                    ),
                )
            )
            self.assertIn(
                'WHERE %s' % editor.quote_name('pub_date'),
                str(index.create_sql(Article, schema_editor=editor))
            )
            editor.add_index(index=index, model=Article)
            self.assertIn(index.name, connection.introspection.get_constraints(
                cursor=connection.cursor(), table_name=Article._meta.db_table,
            ))
            editor.remove_index(index=index, model=Article)

    def test_integer_restriction_partial(self):
        with connection.schema_editor() as editor:
            index = Index(
                name='recent_article_idx',
                fields=['id'],
                condition=Q(pk__gt=1),
            )
            self.assertIn(
                'WHERE %s' % editor.quote_name('id'),
                str(index.create_sql(Article, schema_editor=editor))
            )
            editor.add_index(index=index, model=Article)
            self.assertIn(index.name, connection.introspection.get_constraints(
                cursor=connection.cursor(), table_name=Article._meta.db_table,
            ))
            editor.remove_index(index=index, model=Article)

    def test_boolean_restriction_partial(self):
        with connection.schema_editor() as editor:
            index = Index(
                name='published_index',
                fields=['published'],
                condition=Q(published=True),
            )
            self.assertIn(
                'WHERE %s' % editor.quote_name('published'),
                str(index.create_sql(Article, schema_editor=editor))
            )
            editor.add_index(index=index, model=Article)
            self.assertIn(index.name, connection.introspection.get_constraints(
                cursor=connection.cursor(), table_name=Article._meta.db_table,
            ))
            editor.remove_index(index=index, model=Article)

    @skipUnlessDBFeature('supports_functions_in_partial_indexes')
    def test_multiple_conditions(self):
        with connection.schema_editor() as editor:
            index = Index(
                name='recent_article_idx',
                fields=['pub_date', 'headline'],
                condition=(
                    Q(pub_date__gt=datetime.datetime(
                        year=2015,
                        month=1,
                        day=1,
                        tzinfo=timezone.get_current_timezone(),
                    )) & Q(headline__contains='China')
                ),
            )
            sql = str(index.create_sql(Article, schema_editor=editor))
            where = sql.find('WHERE')
            self.assertIn(
                'WHERE (%s' % editor.quote_name('pub_date'),
                sql
            )
            # Because each backend has different syntax for the operators,
            # check ONLY the occurrence of headline in the SQL.
            self.assertGreater(sql.rfind('headline'), where)
            editor.add_index(index=index, model=Article)
            self.assertIn(index.name, connection.introspection.get_constraints(
                cursor=connection.cursor(), table_name=Article._meta.db_table,
            ))
            editor.remove_index(index=index, model=Article)

    def test_is_null_condition(self):
        with connection.schema_editor() as editor:
            index = Index(
                name='recent_article_idx',
                fields=['pub_date'],
                condition=Q(pub_date__isnull=False),
            )
            self.assertIn(
                'WHERE %s IS NOT NULL' % editor.quote_name('pub_date'),
                str(index.create_sql(Article, schema_editor=editor))
            )
            editor.add_index(index=index, model=Article)
            self.assertIn(index.name, connection.introspection.get_constraints(
                cursor=connection.cursor(), table_name=Article._meta.db_table,
            ))
            editor.remove_index(index=index, model=Article)
