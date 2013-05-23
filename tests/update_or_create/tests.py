from __future__ import absolute_import

import traceback

from django.db.utils import IntegrityError
from django.test import TestCase, TransactionTestCase

from .models import SalesRank, ManualPrimaryKeyTest, Product


class UpdateOrCreateTests(TestCase):

    def test_update(self):
        SalesRank.objects.create(
            product_name='Pony', total_rank=10,
        )
        p, created = SalesRank.objects.update_or_create(
            product_name='Pony', defaults={
                'total_rank': 20
            }
        )
        self.assertFalse(created)
        self.assertEqual(p.product_name, 'Pony')
        self.assertEqual(p.total_rank, 20)

    def test_create(self):
        p, created = SalesRank.objects.update_or_create(
            product_name='Guitar', defaults={
                'total_rank': 1000
            }
        )
        self.assertTrue(created)
        self.assertEqual(p.product_name, 'Guitar')
        self.assertEqual(p.total_rank, 1000)

    def test_create_twice(self):
        SalesRank.objects.update_or_create(product_name='Bicycle', total_rank=20)
        # If we execute the exact same statement, it won't create a SalesRank.
        p, created = SalesRank.objects.update_or_create(product_name='Bicycle', total_rank=20)
        self.assertFalse(created)

    def test_integrity(self):
        # If you don't specify a value or default value for all required
        # fields, you will get an error.
        self.assertRaises(IntegrityError, SalesRank.objects.update_or_create, product_name='Car')

    def test_mananual_primary_key_test(self):
        # If you specify an existing primary key, but different other fields,
        # then you will get an error and data will not be updated.
        ManualPrimaryKeyTest.objects.create(id=1, data="Original")
        self.assertRaises(IntegrityError,
                          ManualPrimaryKeyTest.objects.get_or_create, id=1, data="Different"
        )
        self.assertEqual(ManualPrimaryKeyTest.objects.get(id=1).data, "Original")

    def test_error_contains_full_traceback(self):
        # update_or_create should raise IntegrityErrors with the full traceback.
        # This is tested by checking that a known method call is in the traceback.
        # We cannot use assertRaises/assertRaises here because we need to inspect
        # the actual traceback. Refs #16340.
        try:
            ManualPrimaryKeyTest.objects.get_or_create(id=1, data="Different")
        except IntegrityError as e:
            formatted_traceback = traceback.format_exc()
            self.assertIn('obj.save', formatted_traceback)


class GetOrCreateTransactionTests(TransactionTestCase):

    def test_get_or_create_integrityerror(self):
        # Regression test for #15117. Requires a TransactionTestCase on
        # databases that delay integrity checks until the end of transactions,
        # otherwise the exception is never raised.
        try:
            Product.objects.get_or_create(sales_rank=SalesRank(id=1))
        except IntegrityError:
            pass
        else:
            self.skipTest("This backend does not support integrity checks.")
