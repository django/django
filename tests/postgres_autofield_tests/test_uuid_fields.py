import unittest
import uuid

from django.apps import apps
from django.db import connection
from django.test import TestCase, modify_settings, override_settings

from .models import PSQLAutoIDModel


@override_settings(
    DEFAULT_AUTO_FIELD="django.db.models.SmallAutoField",
)
@modify_settings(INSTALLED_APPS={"append": "django.contrib.postgres"})
@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
class TestAppLevelUUIDv4AutoField(TestCase):
    def test_app_default_auto_field_uuid_v4(self):
        app_label = PSQLAutoIDModel._meta.app_label
        app = apps.get_app_config(app_label=app_label)
        self.assertEqual(
            app.default_auto_field, "django.contrib.postgres.fields.uuid.UUID4AutoField"
        )

        obj = PSQLAutoIDModel.objects.create()
        self.assertIsInstance(obj.id, uuid.UUID)
