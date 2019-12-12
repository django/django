from unittest import mock

from django.core.checks.database import check_database_backends
from django.db import connections, models
from django.test import TestCase
from django.test.utils import isolate_apps, override_settings


class TestRouter:
    """
    Routes to the 'other' database if the model name starts with 'Other'.
    """
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == ('other' if model_name.startswith('other') else 'default')


@isolate_apps('check_framework', attr_name='apps')
class TestMultiDBChecks(TestCase):
    databases = {'default', 'other'}

    def _patch_check_field_on(self, db):
        return mock.patch.object(connections[db].validation, 'check_field')

    @override_settings(DATABASE_ROUTERS=[TestRouter()])
    def test_checks_called_on_the_default_database(self):
        class Model(models.Model):
            field = models.CharField(max_length=100)

        with self._patch_check_field_on('default') as mock_check_field_default:
            with self._patch_check_field_on('other') as mock_check_field_other:
                check_database_backends(app_configs=self.apps.get_app_configs())
                self.assertTrue(mock_check_field_default.called)
                self.assertFalse(mock_check_field_other.called)

    @override_settings(DATABASE_ROUTERS=[TestRouter()])
    def test_checks_called_on_the_other_database(self):
        class OtherModel(models.Model):
            field = models.CharField(max_length=100)

        with self._patch_check_field_on('other') as mock_check_field_other:
            with self._patch_check_field_on('default') as mock_check_field_default:
                check_database_backends(app_configs=self.apps.get_app_configs())
                self.assertTrue(mock_check_field_other.called)
                self.assertFalse(mock_check_field_default.called)

    def test_database_kwarg(self):
        class Model(models.Model):
            field = models.CharField(max_length=100)

        with self._patch_check_field_on('other') as mock_check_field_other:
            with self._patch_check_field_on('default') as mock_check_field_default:
                check_database_backends(
                    app_configs=self.apps.get_app_configs(), database='other',
                )
                self.assertTrue(mock_check_field_other.called)
                self.assertFalse(mock_check_field_default.called)
