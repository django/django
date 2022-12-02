from django.db import connection
from django.test import modify_settings

from . import PostgreSQLTestCase
from .models import CharFieldModel, TextFieldModel


@modify_settings(INSTALLED_APPS={"append": "django.contrib.postgres"})
class UnaccentTest(PostgreSQLTestCase):

    Model = CharFieldModel

    @classmethod
    def setUpTestData(cls):
        cls.Model.objects.bulk_create(
            [
                cls.Model(field="àéÖ"),
                cls.Model(field="aeO"),
                cls.Model(field="aeo"),
            ]
        )

    def test_unaccent(self):
        self.assertQuerySetEqual(
            self.Model.objects.filter(field__unaccent="aeO"),
            ["àéÖ", "aeO"],
            transform=lambda instance: instance.field,
            ordered=False,
        )

    def test_unaccent_chained(self):
        """
        Unaccent can be used chained with a lookup (which should be the case
        since unaccent implements the Transform API)
        """
        self.assertQuerySetEqual(
            self.Model.objects.filter(field__unaccent__iexact="aeO"),
            ["àéÖ", "aeO", "aeo"],
            transform=lambda instance: instance.field,
            ordered=False,
        )
        self.assertQuerySetEqual(
            self.Model.objects.filter(field__unaccent__endswith="éÖ"),
            ["àéÖ", "aeO"],
            transform=lambda instance: instance.field,
            ordered=False,
        )

    def test_unaccent_with_conforming_strings_off(self):
        """SQL is valid when standard_conforming_strings is off."""
        with connection.cursor() as cursor:
            cursor.execute("SHOW standard_conforming_strings")
            disable_conforming_strings = cursor.fetchall()[0][0] == "on"
            if disable_conforming_strings:
                cursor.execute("SET standard_conforming_strings TO off")
            try:
                self.assertQuerySetEqual(
                    self.Model.objects.filter(field__unaccent__endswith="éÖ"),
                    ["àéÖ", "aeO"],
                    transform=lambda instance: instance.field,
                    ordered=False,
                )
            finally:
                if disable_conforming_strings:
                    cursor.execute("SET standard_conforming_strings TO on")

    def test_unaccent_accentuated_needle(self):
        self.assertQuerySetEqual(
            self.Model.objects.filter(field__unaccent="aéÖ"),
            ["àéÖ", "aeO"],
            transform=lambda instance: instance.field,
            ordered=False,
        )


class UnaccentTextFieldTest(UnaccentTest):
    """
    TextField should have the exact same behavior as CharField
    regarding unaccent lookups.
    """

    Model = TextFieldModel
