import re
from unittest import skipUnless

from django.core.management.color import no_style
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models.loading import load_app
from django.test import TestCase

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

    @skipUnless(connections[DEFAULT_DB_ALIAS].vendor == 'postgresql',
                "This is a postgresql-specific issue")
    def test_postgresql_pk_char_indexes(self):
        """Test creation of primary key char indexes on PostgresSQL (#19750)"""
        try:
            module = load_app("indexes.conflict_pk_char_indexes")
        except Exception:
            self.fail('Unable to load conflict_pk_char_indexes module')
        connection = connections[DEFAULT_DB_ALIAS]
        index_sql = connection.creation.sql_indexes_for_model(module.Organization, no_style()) + \
                    connection.creation.sql_indexes_for_model(module.OrganizationType, no_style())
        indexes = [re.search(r'^CREATE INDEX "([^"]+)"', sql).group(1) for sql in index_sql]
        self.assertEqual(len(set(indexes)), 3)
