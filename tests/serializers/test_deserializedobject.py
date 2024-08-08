import json

from django.core import serializers
from django.core.serializers.base import DeserializedObject
from django.test import SimpleTestCase

from .models import Author


class TestDeserializedObjectTests(SimpleTestCase):
    def test_repr(self):
        author = Author(name="John", pk=1)
        deserial_obj = DeserializedObject(obj=author)
        self.assertEqual(
            repr(deserial_obj), "<DeserializedObject: serializers.Author(pk=1)>"
        )

    def test_custom_deserializer(self):
        class CustomDeserializer(serializers.python.Deserializer):
            @staticmethod
            def _get_model(model_identifier):
                return Author

        test_string = """
            [
                {
                    "pk": 1,
                    "model": "serializers.author2",
                    "fields": {
                        "name": "Jane"
                    }
                }
            ]
        """
        deserializer = CustomDeserializer(json.loads(test_string), ignore=False)
        result = next(iter(deserializer))
        deserialized_object = result.object
        author = Author(name="Jane", pk=1)
        self.assertEqual(
            author,
            deserialized_object,
        )
