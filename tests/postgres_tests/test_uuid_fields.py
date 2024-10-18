import uuid

from django.db import connection, models
from django.test import override_settings
from django.test.utils import CaptureQueriesContext

from . import PostgreSQLTestCase
from .fields import UUID4AutoField, UUID4Field
from .models import UUIDv4DBSetModel


class TestUUID4Field(PostgreSQLTestCase):
    def test_uuid_generated_in_db_is_a_correct_uuid(self):
        self.assertIsInstance(UUIDv4DBSetModel._meta.pk, UUID4Field)

        with CaptureQueriesContext(connection) as queries:
            obj1 = UUIDv4DBSetModel.objects.create()

        self.assertEqual(len(queries), 1)
        expected_stmt = 'INSERT INTO "postgres_tests_uuidv4dbsetmodel" ("id") VALUES (DEFAULT) RETURNING "postgres_tests_uuidv4dbsetmodel"."id"'  # noqa
        actual_stmt = queries[0]["sql"]
        self.assertEqual(expected_stmt, actual_stmt)

        obj2 = UUIDv4DBSetModel.objects.create()

        ids = sorted(UUIDv4DBSetModel.objects.values_list("id", flat=True).distinct())
        self.assertEqual(sorted([obj1.id, obj2.id]), ids)
        self.assertIsInstance(obj1.id, uuid.UUID)


class TestUUID4AutoField(PostgreSQLTestCase):
    @override_settings(
        DEFAULT_AUTO_FIELD="django.contrib.postgres.fields.UUID4AutoField"
    )
    def test_default_auto_field_setting(self):
        class PostgresUUID4AutoFieldModel(models.Model):
            pass

        self.assertIsInstance(PostgresUUID4AutoFieldModel._meta.pk, UUID4AutoField)
