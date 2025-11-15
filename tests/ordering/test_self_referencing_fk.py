"""
Test for self-referencing foreign key ordering bug.
"""
from django.test import TestCase

from .models import OneModel, TwoModel


class SelfReferencingForeignKeyOrderingTests(TestCase):
    """
    Tests for ordering by _id field on self-referencing foreign keys.

    Regression test for: Self referencing foreign key doesn't correctly
    order by a relation "_id" field.
    """

    @classmethod
    def setUpTestData(cls):
        # Create test data
        cls.one1 = OneModel.objects.create(oneval=1, root=None)
        cls.one2 = OneModel.objects.create(oneval=2, root=cls.one1)
        cls.one3 = OneModel.objects.create(oneval=3, root=cls.one2)

        cls.two1 = TwoModel.objects.create(record=cls.one1, twoval=10)
        cls.two2 = TwoModel.objects.create(record=cls.one2, twoval=20)
        cls.two3 = TwoModel.objects.create(record=cls.one3, twoval=30)

    def test_order_by_self_referencing_fk_id_field(self):
        """
        Test ordering by _id field on a self-referencing foreign key.

        When ordering by record__root_id, it should:
        1. Use ASC order (not DESC from OneModel.Meta.ordering)
        2. Use a single INNER JOIN (not an extra LEFT OUTER JOIN)
        3. Order by the root_id column directly
        """
        qs = TwoModel.objects.filter(record__oneval__in=[1, 2, 3])
        qs = qs.order_by("record__root_id")

        # Get the SQL query
        sql = str(qs.query)

        # The query should have ascending order, not descending
        # It should NOT have "ORDER BY T3.id DESC" or similar
        # It should have "ORDER BY ... ASC" or just order by the root_id column

        # Check that there's only ONE join (INNER JOIN), not two
        # Count the number of JOIN clauses
        join_count = sql.upper().count(' JOIN ')
        self.assertEqual(
            join_count, 1,
            f"Expected 1 JOIN but found {join_count}. SQL: {sql}"
        )

        # The query should not have a LEFT OUTER JOIN
        self.assertNotIn(
            'LEFT OUTER JOIN', sql.upper(),
            f"Unexpected LEFT OUTER JOIN in query. SQL: {sql}"
        )

        # The ORDER BY should be ascending (ASC or implicit)
        # and should reference the root_id column directly
        self.assertIn('ORDER BY', sql.upper())

        # Split to get the ORDER BY clause
        order_by_part = sql.upper().split('ORDER BY')[1].strip()

        # It should not end with DESC (from the model's default ordering)
        # If the bug is present, it will have "T3"."id" DESC or similar
        self.assertNotRegex(
            order_by_part,
            r'T\d+.*DESC',
            f"ORDER BY clause has unexpected DESC with aliased table. SQL: {sql}"
        )

    def test_order_by_self_referencing_fk_id_field_desc(self):
        """
        Test ordering by -record__root_id (descending).

        When explicitly ordering descending, it should respect that order,
        not invert it based on the model's default ordering.
        """
        qs = TwoModel.objects.filter(record__oneval__in=[1, 2, 3])
        qs = qs.order_by("-record__root_id")

        sql = str(qs.query)

        # Should still have only one JOIN
        join_count = sql.upper().count(' JOIN ')
        self.assertEqual(
            join_count, 1,
            f"Expected 1 JOIN but found {join_count}. SQL: {sql}"
        )

        # Should not have LEFT OUTER JOIN
        self.assertNotIn(
            'LEFT OUTER JOIN', sql.upper(),
            f"Unexpected LEFT OUTER JOIN in query. SQL: {sql}"
        )

        # The ORDER BY should be explicitly descending
        order_by_part = sql.upper().split('ORDER BY')[1].strip()
        self.assertIn('DESC', order_by_part)

    def test_order_by_self_referencing_fk_id_field_via_double_underscore_id(self):
        """
        Test ordering by record__root__id (with __id at the end).

        This should work correctly and produce optimal SQL.
        """
        qs = TwoModel.objects.filter(record__oneval__in=[1, 2, 3])
        qs = qs.order_by("record__root__id")

        sql = str(qs.query)

        # Should have only one JOIN
        join_count = sql.upper().count(' JOIN ')
        self.assertEqual(
            join_count, 1,
            f"Expected 1 JOIN but found {join_count}. SQL: {sql}"
        )

        # Should reference root_id column directly
        self.assertIn('root_id', sql.lower())
