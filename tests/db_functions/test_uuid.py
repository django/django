import uuid

from django.db import NotSupportedError, connection
from django.db.models.functions import UUID4, UUID7
from django.test import TestCase
from django.test.testcases import skipIfDBFeature, skipUnlessDBFeature

from .models import UUIDModel


class TestUUID(TestCase):
    @skipUnlessDBFeature("supports_uuid4_function")
    def test_uuid4(self):
        m1 = UUIDModel.objects.create()
        m2 = UUIDModel.objects.create()
        UUIDModel.objects.update(uuid=UUID4())
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertIsInstance(m1.uuid, uuid.UUID)
        self.assertEqual(m1.uuid.version, 4)
        self.assertNotEqual(m1.uuid, m2.uuid)

    @skipUnlessDBFeature("supports_uuid7_function")
    def test_uuid7(self):
        m1 = UUIDModel.objects.create()
        m2 = UUIDModel.objects.create()
        UUIDModel.objects.update(uuid=UUID7())
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertIsInstance(m1.uuid, uuid.UUID)
        self.assertEqual(m1.uuid.version, 7)
        self.assertNotEqual(m1.uuid, m2.uuid)

    @skipIfDBFeature("supports_uuid4_function")
    def test_uuid4_unsupported(self):
        if connection.vendor == "mysql":
            if connection.mysql_is_mariadb:
                msg = "UUID4 requires MariaDB version 11.7 or later."
            else:
                msg = "UUID4 is not supported on MySQL."
        elif connection.vendor == "oracle":
            msg = "UUID4 requires Oracle version 23ai/26ai (23.9) or later."
        else:
            msg = "UUID4 is not supported on this database backend."

        with self.assertRaisesMessage(NotSupportedError, msg):
            UUIDModel.objects.update(uuid=UUID4())

    @skipIfDBFeature("supports_uuid7_function")
    def test_uuid7_unsupported(self):
        if connection.vendor == "mysql":
            if connection.mysql_is_mariadb:
                msg = "UUID7 requires MariaDB version 11.7 or later."
            else:
                msg = "UUID7 is not supported on MySQL."
        elif connection.vendor == "postgresql":
            msg = "UUID7 requires PostgreSQL version 18 or later."
        elif connection.vendor == "sqlite":
            msg = "UUID7 on SQLite requires Python version 3.14 or later."
        else:
            msg = "UUID7 is not supported on this database backend."

        with self.assertRaisesMessage(NotSupportedError, msg):
            UUIDModel.objects.update(uuid=UUID7())
