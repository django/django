# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.core.checks import Error
from django.db import connections, models
from django.test import mock

from .base import IsolatedModelsTestCase


def dummy_allow_migrate(db, app_label, **hints):
    # Prevent checks from being run on the 'other' database, which doesn't have
    # its check_field() method mocked in the test.
    return db == 'default'


class BackendSpecificChecksTests(IsolatedModelsTestCase):

    @mock.patch('django.db.models.fields.router.allow_migrate', new=dummy_allow_migrate)
    def test_check_field(self):
        """ Test if backend specific checks are performed. """
        error = Error('an error', hint=None)

        class Model(models.Model):
            field = models.IntegerField()

        field = Model._meta.get_field('field')
        with mock.patch.object(connections['default'].validation, 'check_field', return_value=[error]):
            errors = field.check()

        self.assertEqual(errors, [error])
