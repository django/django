import unittest

from django.db import connection
from django.db.models.expressions import RawSQL
from django.test import TestCase

from ..models import Square


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL tests")
class BulkCreateUnnestTests(TestCase):
    def test_single_object(self):
        with self.assertNumQueries(1) as ctx:
            Square.objects.bulk_create([Square(root=2, square=4)])
        self.assertNotIn("UNNEST", ctx[0]["sql"])

    def test_non_literal(self):
        with self.assertNumQueries(1) as ctx:
            Square.objects.bulk_create(
                [Square(root=2, square=RawSQL("%s", (4,))), Square(root=3, square=9)]
            )
        self.assertNotIn("UNNEST", ctx[0]["sql"])

    def test_unnest_eligible(self):
        with self.assertNumQueries(1) as ctx:
            Square.objects.bulk_create(
                [Square(root=2, square=4), Square(root=3, square=9)]
            )
        self.assertIn("UNNEST", ctx[0]["sql"])
