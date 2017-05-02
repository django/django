from __future__ import absolute_import

from django.test import TestCase

from .models import Movie


class GetFieldDisplayTests(TestCase):

    def test_mixed_type(self):
        # Regression test for #20749. Ensure that get_field_display still
        # returns a choice's display value even if the type of the value does
        # not align with the type of the field.
        movie = Movie(genre=1)
        self.assertEqual(movie.get_genre_display(), 'Action')
        self.assertNotEqual(movie.get_genre_display(), '1')
