from django.db import connection
from django.db.models import Value
from django.db.models.functions import Length, LPad, RPad
from django.test import TestCase

from ..models import Author


class PadTests(TestCase):
    def test_pad(self):
        Author.objects.create(name='John', alias='j')
        none_value = '' if connection.features.interprets_empty_strings_as_nulls else None
        tests = (
            (LPad('name', 7, Value('xy')), 'xyxJohn'),
            (RPad('name', 7, Value('xy')), 'Johnxyx'),
            (LPad('name', 6, Value('x')), 'xxJohn'),
            (RPad('name', 6, Value('x')), 'Johnxx'),
            # The default pad string is a space.
            (LPad('name', 6), '  John'),
            (RPad('name', 6), 'John  '),
            # If string is longer than length it is truncated.
            (LPad('name', 2), 'Jo'),
            (RPad('name', 2), 'Jo'),
            (LPad('name', 0), ''),
            (RPad('name', 0), ''),
            (LPad('name', None), none_value),
            (RPad('name', None), none_value),
            (LPad('goes_by', 1), none_value),
            (RPad('goes_by', 1), none_value),
        )
        for function, padded_name in tests:
            with self.subTest(function=function):
                authors = Author.objects.annotate(padded_name=function)
                self.assertQuerysetEqual(authors, [padded_name], lambda a: a.padded_name, ordered=False)

    def test_pad_negative_length(self):
        for function in (LPad, RPad):
            with self.subTest(function=function):
                with self.assertRaisesMessage(ValueError, "'length' must be greater or equal to 0."):
                    function('name', -1)

    def test_combined_with_length(self):
        Author.objects.create(name='Rhonda', alias='john_smith')
        Author.objects.create(name='♥♣♠', alias='bytes')
        authors = Author.objects.annotate(filled=LPad('name', Length('alias')))
        self.assertQuerysetEqual(
            authors.order_by('alias'),
            ['  ♥♣♠', '    Rhonda'],
            lambda a: a.filled,
        )
