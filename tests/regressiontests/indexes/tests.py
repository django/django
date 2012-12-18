from django.core.management.color import no_style
from django.db import connections, DEFAULT_DB_ALIAS
from django.test import TestCase

from .models import Article


class IndexesTests(TestCase):
    def test_index_together(self):
        connection = connections[DEFAULT_DB_ALIAS]
        index_sql = connection.creation.sql_indexes_for_model(Article, no_style())
        self.assertEqual(len(index_sql), 1)
