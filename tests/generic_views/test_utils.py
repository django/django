from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase
from django.views.generic.utils import get_field_from_path

from .models import Artist, Book


class TestGenericViewUtils(TestCase):
    def test_get_field_from_path(self):
        # test that a field on the model is returned
        self.assertEqual(
            get_field_from_path(Book, "name").name,
            Book._meta.get_field("name").name,
        )
        # test that a field on a related model is returned
        self.assertEqual(
            get_field_from_path(Book, "artist__birthday").name,
            Artist._meta.get_field("birthday").name,
        )
        # test that a non-existent field raises FieldDoesNotExist
        with self.assertRaises(FieldDoesNotExist):
            get_field_from_path(Book, "artist__non_existent_field")
