from unittest import skipUnless

from django.core.management.color import no_style
from django.db import connection
from django.test import TestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango110Warning

from .models import Article, ArticleTranslation, IndexTogetherSingleList


@ignore_warnings(category=RemovedInDjango110Warning)
class CreationIndexesTests(TestCase):
    """
    Test index handling by the to-be-deprecated connection.creation interface.
    """
    def test_index_together(self):
        index_sql = connection.creation.sql_indexes_for_model(Article, no_style())
        self.assertEqual(len(index_sql), 1)

    def test_index_together_single_list(self):
        # Test for using index_together with a single list (#22172)
        index_sql = connection.creation.sql_indexes_for_model(IndexTogetherSingleList, no_style())
        self.assertEqual(len(index_sql), 1)

    @skipUnless(connection.vendor == 'postgresql',
        "This is a postgresql-specific issue")
    def test_postgresql_text_indexes(self):
        """Test creation of PostgreSQL-specific text indexes (#12234)"""
        from .models import IndexedArticle
        index_sql = connection.creation.sql_indexes_for_model(IndexedArticle, no_style())
        self.assertEqual(len(index_sql), 5)
        self.assertIn('("headline" varchar_pattern_ops)', index_sql[1])
        self.assertIn('("body" text_pattern_ops)', index_sql[3])
        # unique=True and db_index=True should only create the varchar-specific
        # index (#19441).
        self.assertIn('("slug" varchar_pattern_ops)', index_sql[4])

    @skipUnless(connection.vendor == 'postgresql',
        "This is a postgresql-specific issue")
    def test_postgresql_virtual_relation_indexes(self):
        """Test indexes are not created for related objects"""
        index_sql = connection.creation.sql_indexes_for_model(Article, no_style())
        self.assertEqual(len(index_sql), 1)


class SchemaIndexesTests(TestCase):
    """
    Test index handling by the db.backends.schema infrastructure.
    """
    def test_index_together(self):
        editor = connection.schema_editor()
        index_sql = editor._model_indexes_sql(Article)
        self.assertEqual(len(index_sql), 1)
        # Ensure the index name is properly quoted
        self.assertIn(
            connection.ops.quote_name(
                editor._create_index_name(Article, ['headline', 'pub_date'], suffix='_idx')
            ),
            index_sql[0]
        )

    def test_index_together_single_list(self):
        # Test for using index_together with a single list (#22172)
        index_sql = connection.schema_editor()._model_indexes_sql(IndexTogetherSingleList)
        self.assertEqual(len(index_sql), 1)

    @skipUnless(connection.vendor == 'postgresql',
        "This is a postgresql-specific issue")
    def test_postgresql_text_indexes(self):
        """Test creation of PostgreSQL-specific text indexes (#12234)"""
        from .models import IndexedArticle
        index_sql = connection.schema_editor()._model_indexes_sql(IndexedArticle)
        self.assertEqual(len(index_sql), 5)
        self.assertIn('("headline" varchar_pattern_ops)', index_sql[2])
        self.assertIn('("body" text_pattern_ops)', index_sql[3])
        # unique=True and db_index=True should only create the varchar-specific
        # index (#19441).
        self.assertIn('("slug" varchar_pattern_ops)', index_sql[4])

    @skipUnless(connection.vendor == 'postgresql',
        "This is a postgresql-specific issue")
    def test_postgresql_virtual_relation_indexes(self):
        """Test indexes are not created for related objects"""
        index_sql = connection.schema_editor()._model_indexes_sql(Article)
        self.assertEqual(len(index_sql), 1)

    @skipUnless(connection.vendor == 'mysql', "This is a mysql-specific issue")
    def test_no_index_for_foreignkey(self):
        """
        MySQL on InnoDB already creates indexes automatically for foreign keys.
        (#14180).
        """
        storage = connection.introspection.get_storage_engine(
            connection.cursor(), ArticleTranslation._meta.db_table
        )
        if storage != "InnoDB":
            self.skip("This test only applies to the InnoDB storage engine")
        index_sql = connection.schema_editor()._model_indexes_sql(ArticleTranslation)
        self.assertEqual(index_sql, [])
