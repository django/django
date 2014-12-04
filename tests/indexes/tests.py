from unittest import skipUnless

from django.db import connection
from django.test import TestCase

from .models import Article, IndexTogetherSingleList


class IndexesTests(TestCase):
    def test_index_together(self):
        index_sql = connection.schema_editor()._model_indexes_sql(Article)
        self.assertEqual(len(index_sql), 1)

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
