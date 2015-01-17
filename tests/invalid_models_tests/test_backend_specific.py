# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from types import MethodType

from django.core.checks import Error
from django.db import connection, models

from .base import IsolatedModelsTestCase


class BackendSpecificChecksTests(IsolatedModelsTestCase):

    def test_check_field(self):
        """ Test if backend specific checks are performed. """

        error = Error('an error', hint=None)

        def mock(self, field, **kwargs):
            return [error]

        class Model(models.Model):
            field = models.IntegerField()

        field = Model._meta.get_field('field')

        # Mock connection.validation.check_field method.
        v = connection.validation
        old_check_field = v.check_field
        v.check_field = MethodType(mock, v)
        try:
            errors = field.check()
        finally:
            # Unmock connection.validation.check_field method.
            v.check_field = old_check_field

        self.assertEqual(errors, [error])
