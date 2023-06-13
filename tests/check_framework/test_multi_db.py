from unittest import mock

from django.db import connections, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps, override_settings


class TestRouter:
    """
    Routes to the 'other' database if the model name starts with 'Other'.
    """

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == ("other" if model_name.startswith("other") else "default")


@override_settings(DATABASE_ROUTERS=[TestRouter()])
@isolate_apps("check_framework")
class TestMultiDBChecks(SimpleTestCase):
    def _patch_check_field_on(self, db):
        return mock.patch.object(connections[db].validation, "check_field")

    def test_checks_called_on_the_default_database(self):
        class Model(models.Model):
            field = models.CharField(max_length=100)

        model = Model()
        with self._patch_check_field_on("default") as mock_check_field_default:
            with self._patch_check_field_on("other") as mock_check_field_other:
                model.check(databases={"default", "other"})
                self.assertTrue(mock_check_field_default.called)
                self.assertFalse(mock_check_field_other.called)

    def test_checks_called_on_the_other_database(self):
        class OtherModel(models.Model):
            field = models.CharField(max_length=100)

        model = OtherModel()
        with self._patch_check_field_on("other") as mock_check_field_other:
            with self._patch_check_field_on("default") as mock_check_field_default:
                model.check(databases={"default", "other"})
                self.assertTrue(mock_check_field_other.called)
                self.assertFalse(mock_check_field_default.called)
