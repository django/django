from unittest import skipUnless

from django.db import connection
from django.db.models import Index
from django.test import TestCase

from ..utils import postgis
from .models import City


class SchemaIndexesTests(TestCase):
    @skipUnless(postgis, 'This is a PostGIS-specific test.')
    def test_using_sql(self):
        index = Index(fields=['point'])
        editor = connection.schema_editor()
        self.assertIn(
            '%s USING ' % editor.quote_name(City._meta.db_table),
            str(index.create_sql(City, editor)),
        )
