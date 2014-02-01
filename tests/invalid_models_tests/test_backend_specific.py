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

    def test_validate_field(self):
        """ Errors raised by deprecated `validate_field` method should be
        collected. """

        def mock(self, errors, opts, field):
            errors.add(opts, "An error!")

        class Model(models.Model):
            field = models.IntegerField()

        field = Model._meta.get_field('field')
        expected = [
            Error(
                "An error!",
                hint=None,
                obj=field,
            )
        ]

        # Mock connection.validation.validate_field method.
        v = connection.validation
        old_validate_field = v.validate_field
        v.validate_field = MethodType(mock, v)
        try:
            errors = field.check()
        finally:
            # Unmock connection.validation.validate_field method.
            v.validate_field = old_validate_field

        self.assertEqual(errors, expected)
