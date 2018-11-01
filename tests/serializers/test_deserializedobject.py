from django.core.serializers.base import DeserializedObject
from django.test import SimpleTestCase

from .models import Author


class TestDeserializedObjectTests(SimpleTestCase):

    def test_repr(self):
        author = Author(name='John', pk=1)
        deserial_obj = DeserializedObject(obj=author)
        self.assertEqual(repr(deserial_obj), '<DeserializedObject: serializers.Author(pk=1)>')
