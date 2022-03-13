from django.db import connection
from django.db.models import Value
from django.db.models.functions import Length, Repeat
from django.test import TestCase

from ..models import Author


class RepeatTests(TestCase):
    def test_basic(self):
        Author.objects.create(name="John", alias="xyz")
        none_value = (
            "" if connection.features.interprets_empty_strings_as_nulls else None
        )
        tests = (
            (Repeat("name", 0), ""),
            (Repeat("name", 2), "JohnJohn"),
            (Repeat("name", Length("alias")), "JohnJohnJohn"),
            (Repeat(Value("x"), 3), "xxx"),
            (Repeat("name", None), none_value),
            (Repeat(Value(None), 4), none_value),
            (Repeat("goes_by", 1), none_value),
        )
        for function, repeated_text in tests:
            with self.subTest(function=function):
                authors = Author.objects.annotate(repeated_text=function)
                self.assertQuerysetEqual(
                    authors, [repeated_text], lambda a: a.repeated_text, ordered=False
                )

    def test_negative_number(self):
        with self.assertRaisesMessage(
            ValueError, "'number' must be greater or equal to 0."
        ):
            Repeat("name", -1)
