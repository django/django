from datetime import datetime
from time import sleep

from django.contrib.postgres.functions import TransactionNow

from . import PostgreSQLTestCase
from .models import NowTestModel


class TestTransactionNow(PostgreSQLTestCase):

    def test_transaction_now(self):
        """
        The test case puts everything under a transaction, so two models
        updated with a short gap should have the same time.
        """
        m1 = NowTestModel.objects.create()
        m2 = NowTestModel.objects.create()

        NowTestModel.objects.filter(id=m1.id).update(when=TransactionNow())
        sleep(0.1)
        NowTestModel.objects.filter(id=m2.id).update(when=TransactionNow())

        m1.refresh_from_db()
        m2.refresh_from_db()

        self.assertIsInstance(m1.when, datetime)
        self.assertEqual(m1.when, m2.when)
