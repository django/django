from django.db.models import IntegerField, Value
from django.db.models.functions import Left, Lower
from django.test import TestCase
from django.test import skipUnlessDBFeature, skipIfDBFeature

from ..models import Author


class LeftTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(name="John Smith", alias="smithj")
        Author.objects.create(name="Rhonda")

    def test_basic(self):
        authors = Author.objects.annotate(name_part=Left("name", 5))
        self.assertQuerySetEqual(
            authors.order_by("name"), ["John ", "Rhond"], lambda a: a.name_part
        )
        # If alias is null, set it to the first 2 lower characters of the name.
        Author.objects.filter(alias__isnull=True).update(alias=Lower(Left("name", 2)))
        self.assertQuerySetEqual(
            authors.order_by("name"), ["smithj", "rh"], lambda a: a.alias
        )

    def test_invalid_length(self):
        with self.assertRaisesMessage(ValueError, "'length' must be greater than 0"):
            Author.objects.annotate(raises=Left("name", 0))

    def test_expressions(self):
        authors = Author.objects.annotate(
            name_part=Left("name", Value(3, output_field=IntegerField()))
        )
        self.assertQuerySetEqual(
            authors.order_by("name"), ["Joh", "Rho"], lambda a: a.name_part
        )

    @skipUnlessDBFeature("supports_negative_indexing")
    def test_left_negative_length(self):
        authors = Author.objects.annotate(
            name_part=Left("name", -5)
        )
        self.assertQuerySetEqual(
            authors.order_by("name"),
            ["John ", "Rh"],
            lambda a: a.name_part,
        )

    @skipUnlessDBFeature("supports_negative_indexing")
    def test_left_negative_length_postgres_accepts(self):
        # Explicit positive check for PostgreSQL acceptance (redundant with
        # test_left_negative_length, but clearer in test output).
        authors = Author.objects.annotate(name_part=Left("name", -5))
        self.assertQuerySetEqual(
            authors.order_by("name"), ["John ", "Rh"], lambda a: a.name_part
        )

    @skipIfDBFeature("supports_negative_indexing")
    def test_left_negative_length_not_supported(self):
        # Non-PostgreSQL backends must reject negative lengths at validation
        # time (Left.__init__ raises ValueError).
        with self.assertRaisesMessage(ValueError, "'length' must be greater than 0"):
            Author.objects.annotate(name_part=Left("name", -5))