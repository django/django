from unittest import mock

from django.core.checks import Error
from django.core.checks.database import check_database_backends
from django.db import connections, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps


def dummy_allow_migrate(db, app_label, **hints):
    # Prevent checks from being run on the 'other' database, which doesn't have
    # its check_field() method mocked in the test.
    return db == 'default'


@isolate_apps('invalid_models_tests', attr_name='apps')
class BackendSpecificChecksTests(SimpleTestCase):

    @mock.patch('django.db.router.allow_migrate', new=dummy_allow_migrate)
    def test_check_field(self):
        """ Test if backend specific checks are performed. """
        error = Error('an error')

        class Model(models.Model):
            pass

        with mock.patch.object(connections['default'].validation, 'check_field', return_value=[error]):
            self.assertEqual(
                check_database_backends(
                    app_configs=self.apps.get_app_configs(),
                ), [error]
            )
