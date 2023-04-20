from unittest import skipUnless

from django.db import connection
from django.db.models import Value
from django.db.models.functions import NullIf
from django.test import TestCase

from ..models import Author


class NullIfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(name="John Smith", alias="smithj")
        Author.objects.create(name="Rhonda", alias="Rhonda")

    def test_basic(self):
        authors = Author.objects.annotate(nullif=NullIf("alias", "name")).values_list(
            "nullif"
        )
        self.assertCountEqual(
            authors,
            [
                ("smithj",),
                (
                    ""
                    if connection.features.interprets_empty_strings_as_nulls
                    else None,
                ),
            ],
        )

    def test_null_argument(self):
        authors = Author.objects.annotate(
            nullif=NullIf("name", Value(None))
        ).values_list("nullif")
        self.assertCountEqual(authors, [("John Smith",), ("Rhonda",)])

    def test_too_few_args(self):
        msg = "'NullIf' takes exactly 2 arguments (1 given)"
        with self.assertRaisesMessage(TypeError, msg):
            NullIf("name")

    @skipUnless(connection.vendor == "oracle", "Oracle specific test for NULL-literal")
    def test_null_literal(self):
        msg = "Oracle does not allow Value(None) for expression1."
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Author.objects.annotate(nullif=NullIf(Value(None), "name")).values_list(
                    "nullif"
                )
            )
