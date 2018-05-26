import unittest

from django.db import connection, router
from django.db.models.sql import InsertQuery
from django.test import TestCase

from ..models import Author, ReturningModel


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL tests')
class ReturningValuesTestCase(TestCase):
    def test_pk_only(self):
        db = router.db_for_write(Author)
        query = InsertQuery(Author)
        query.insert_values(Author._meta.fields, [], raw=False)
        compiler = query.get_compiler(using=db)
        compiler.return_id = True
        sql = compiler.as_sql()[0][0]
        self.assertIn('RETURNING "backends_author"."id"', sql)

    def test_multiple_returning_fields(self):
        db = router.db_for_write(ReturningModel)
        query = InsertQuery(ReturningModel)
        query.insert_values(ReturningModel._meta.fields, [], raw=False)
        compiler = query.get_compiler(using=db)
        compiler.return_id = True
        sql = compiler.as_sql()[0][0]
        self.assertIn(
            'RETURNING "backends_returningmodel"."id", "backends_returningmodel"."created"',
            sql,
        )
