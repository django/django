import uuid
from datetime import datetime
from time import sleep

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.functions import RandomUUID, TransactionNow, Unnest
from django.db.models import CharField

from . import PostgreSQLTestCase
from .models import CharArrayModel, NowTestModel, UUIDTestModel


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


class TestUnnest(PostgreSQLTestCase):
    def test_unnest(self):
        field_values = [
            ["field1", "field2"],
            ["field3"],
            ["field2", "field3"],
            ["field1", "field3"],
            ["field3"],
            ["field1", "field4"],
            ["field2", "field4", "field3"],
        ]
        CharArrayModel.objects.bulk_create(
            [CharArrayModel(field=x) for x in field_values]
        )
        result = (
            CharArrayModel.objects.annotate(
                elements=Unnest(
                    "field",
                    output_field=ArrayField(CharField(max_length=10)),
                )
            )
            .values_list("elements", flat=True)
            .distinct()
        )
        breakpoint()
        self.assertQuerySetEqual(
            result, ["field2", "field4", "field3", "field1"], ordered=False
        )


class TestRandomUUID(PostgreSQLTestCase):
    def test_random_uuid(self):
        m1 = UUIDTestModel.objects.create()
        m2 = UUIDTestModel.objects.create()
        UUIDTestModel.objects.update(uuid=RandomUUID())
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertIsInstance(m1.uuid, uuid.UUID)
        self.assertNotEqual(m1.uuid, m2.uuid)
