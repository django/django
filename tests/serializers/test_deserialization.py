import json
import unittest

from django.core.serializers.base import DeserializationError, DeserializedObject
from django.core.serializers.json import Deserializer as JsonDeserializer
from django.core.serializers.jsonl import Deserializer as JsonlDeserializer
from django.core.serializers.python import Deserializer
from django.test import SimpleTestCase

from .models import Author

try:
    import yaml  # NOQA

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class TestDeserializer(SimpleTestCase):
    def setUp(self):
        self.object_list = [
            {"pk": 1, "model": "serializers.author", "fields": {"name": "Jane"}},
            {"pk": 2, "model": "serializers.author", "fields": {"name": "Joe"}},
        ]
        self.deserializer = Deserializer(self.object_list)
        self.jane = Author(name="Jane", pk=1)
        self.joe = Author(name="Joe", pk=2)

    def test_deserialized_object_repr(self):
        deserial_obj = DeserializedObject(obj=self.jane)
        self.assertEqual(
            repr(deserial_obj), "<DeserializedObject: serializers.Author(pk=1)>"
        )

    def test_next_functionality(self):
        first_item = next(self.deserializer)

        self.assertEqual(first_item.object, self.jane)

        second_item = next(self.deserializer)
        self.assertEqual(second_item.object, self.joe)

        with self.assertRaises(StopIteration):
            next(self.deserializer)

    def test_invalid_model_identifier(self):
        invalid_object_list = [
            {"pk": 1, "model": "serializers.author2", "fields": {"name": "Jane"}}
        ]
        self.deserializer = Deserializer(invalid_object_list)
        with self.assertRaises(DeserializationError):
            next(self.deserializer)

        deserializer = Deserializer(object_list=[])
        with self.assertRaises(StopIteration):
            next(deserializer)

    def test_custom_deserializer(self):
        class CustomDeserializer(Deserializer):
            @staticmethod
            def _get_model_from_node(model_identifier):
                return Author

        deserializer = CustomDeserializer(self.object_list)
        result = next(iter(deserializer))
        deserialized_object = result.object
        self.assertEqual(
            self.jane,
            deserialized_object,
        )

    def test_empty_object_list(self):
        deserializer = Deserializer(object_list=[])
        with self.assertRaises(StopIteration):
            next(deserializer)

    def test_json_bytes_input(self):
        test_string = json.dumps(self.object_list)
        stream = test_string.encode("utf-8")
        deserializer = JsonDeserializer(stream_or_string=stream)

        first_item = next(deserializer)
        second_item = next(deserializer)

        self.assertEqual(first_item.object, self.jane)
        self.assertEqual(second_item.object, self.joe)

    def test_jsonl_bytes_input(self):
        test_string = """
        {"pk": 1, "model": "serializers.author", "fields": {"name": "Jane"}}
        {"pk": 2, "model": "serializers.author", "fields": {"name": "Joe"}}
        {"pk": 3, "model": "serializers.author", "fields": {"name": "John"}}
        {"pk": 4, "model": "serializers.author", "fields": {"name": "Smith"}}"""
        stream = test_string.encode("utf-8")
        deserializer = JsonlDeserializer(stream_or_string=stream)

        first_item = next(deserializer)
        second_item = next(deserializer)

        self.assertEqual(first_item.object, self.jane)
        self.assertEqual(second_item.object, self.joe)

    @unittest.skipUnless(HAS_YAML, "No yaml library detected")
    def test_yaml_bytes_input(self):
        from django.core.serializers.pyyaml import Deserializer as YamlDeserializer

        test_string = """- pk: 1
  model: serializers.author
  fields:
    name: Jane

- pk: 2
  model: serializers.author
  fields:
    name: Joe

- pk: 3
  model: serializers.author
  fields:
    name: John

- pk: 4
  model: serializers.author
  fields:
    name: Smith
"""
        stream = test_string.encode("utf-8")
        deserializer = YamlDeserializer(stream_or_string=stream)

        first_item = next(deserializer)
        second_item = next(deserializer)

        self.assertEqual(first_item.object, self.jane)
        self.assertEqual(second_item.object, self.joe)
