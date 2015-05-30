# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import modify_settings

from . import PostgreSQLTestCase
from .models import CharFieldModel, TextFieldModel


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class UnaccentTest(PostgreSQLTestCase):

    Model = CharFieldModel

    def setUp(self):
        self.Model.objects.bulk_create([
            self.Model(field="àéÖ"),
            self.Model(field="aeO"),
            self.Model(field="aeo"),
        ])

    def test_unaccent(self):
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__unaccent="aeO"),
            ["àéÖ", "aeO"],
            transform=lambda instance: instance.field,
            ordered=False
        )

    def test_unaccent_chained(self):
        """
        Check that unaccent can be used chained with a lookup (which should be
        the case since unaccent implements the Transform API)
        """
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__unaccent__iexact="aeO"),
            ["àéÖ", "aeO", "aeo"],
            transform=lambda instance: instance.field,
            ordered=False
        )
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__unaccent__endswith="éÖ"),
            ["àéÖ", "aeO"],
            transform=lambda instance: instance.field,
            ordered=False
        )

    def test_unaccent_accentuated_needle(self):
        self.assertQuerysetEqual(
            self.Model.objects.filter(field__unaccent="aéÖ"),
            ["àéÖ", "aeO"],
            transform=lambda instance: instance.field,
            ordered=False
        )


class UnaccentTextFieldTest(UnaccentTest):
    """
    TextField should have the exact same behavior as CharField
    regarding unaccent lookups.
    """
    Model = TextFieldModel
