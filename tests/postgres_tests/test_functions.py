import uuid
from datetime import datetime
from datetime import timezone as datetime_timezone
from time import sleep

from django.contrib.postgres.functions import RandomUUID, TransactionNow
from django.db.models import DateTimeField, Func, Value
from django.test import override_settings

from . import PostgreSQLTestCase
from .models import NowTestModel, UUIDTestModel


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


class TestRandomUUID(PostgreSQLTestCase):
    def test_random_uuid(self):
        m1 = UUIDTestModel.objects.create()
        m2 = UUIDTestModel.objects.create()
        UUIDTestModel.objects.update(uuid=RandomUUID())
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertIsInstance(m1.uuid, uuid.UUID)
        self.assertNotEqual(m1.uuid, m2.uuid)


@override_settings(USE_TZ=True, TIME_ZONE="America/New_York")
class TestTimeZoneFunction(PostgreSQLTestCase):
    def test_timezone_function_returns_naive_datetime(self):
        original = datetime(2026, 6, 15, 12, tzinfo=datetime_timezone.utc)
        obj = NowTestModel.objects.create(when=original)
        obj = NowTestModel.objects.annotate(
            local_when=Func(
                Value("Europe/Paris"),
                "when",
                function="timezone",
                output_field=DateTimeField(),
            )
        ).get(pk=obj.pk)

        self.assertEqual(obj.local_when, datetime(2026, 6, 15, 14))
        self.assertIsNone(obj.local_when.tzinfo)

        obj.when = obj.local_when
        with self.assertWarns(RuntimeWarning):
            obj.save()
        obj.refresh_from_db()
        self.assertEqual(
            obj.when,
            datetime(2026, 6, 15, 18, tzinfo=datetime_timezone.utc),
        )
