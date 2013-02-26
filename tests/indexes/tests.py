from django.core.management.color import no_style
from django.db import connections, DEFAULT_DB_ALIAS
from django.test import TestCase
from django.utils.unittest import skipUnless

from .models import Article


class IndexesTests(TestCase):
    def test_index_together(self):
        connection = connections[DEFAULT_DB_ALIAS]
        index_sql = connection.creation.sql_indexes_for_model(Article, no_style())
        self.assertEqual(len(index_sql), 1)

    @skipUnless(connections[DEFAULT_DB_ALIAS].vendor == 'postgresql',
        "This is a postgresql-specific issue")
    def test_postgresql_text_indexes(self):
        """Test creation of PostgreSQL-specific text indexes (#12234)"""
        from .models import IndexedArticle
        connection = connections[DEFAULT_DB_ALIAS]
        index_sql = connection.creation.sql_indexes_for_model(IndexedArticle, no_style())
        self.assertEqual(len(index_sql), 5)
        self.assertIn('("headline" varchar_pattern_ops)', index_sql[1])
        self.assertIn('("body" text_pattern_ops)', index_sql[3])
        # unique=True and db_index=True should only create the varchar-specific
        # index (#19441).
        self.assertIn('("slug" varchar_pattern_ops)', index_sql[4])
