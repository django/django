from django.core import serializers
from django.core.serializers.utils import ClassLookupDict
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature

from .models import Book, EmbeddedAuthor, MyFieldThing


class SerializationTests:
    maxDiff = None

    def test_my_field_thing(self):
        objects = [
            MyFieldThing(name="Foo"),
        ]
        serialized_data = serializers.serialize(
            self.serialization_format, objects, indent=2
        )
        self.assertEqual(serialized_data, self.expected_data["my_field_thing"])
        for obj in serializers.deserialize(self.serialization_format, serialized_data):
            obj.save()
        thing = MyFieldThing.objects.get()
        self.assertEqual(thing.name, "Foo")

    @skipUnlessDBFeature("supports_json_field")
    def test_embedded_model_field(self):
        objects = [
            Book(name="Othello", author=EmbeddedAuthor(name="Shakespeare")),
        ]
        serialized_data = serializers.serialize(
            self.serialization_format, objects, indent=2
        )
        self.assertEqual(serialized_data, self.expected_data["embedded_model_field"])
        for obj in serializers.deserialize(self.serialization_format, serialized_data):
            obj.save()
        book = Book.objects.get()
        self.assertEqual(book.name, "Othello")
        self.assertEqual(book.author.name, "Shakespeare")


class JSONSerializerTests(SerializationTests, TestCase):
    serialization_format = "json"
    expected_data = {
        "embedded_model_field": """[
{
  "model": "serializers.book",
  "pk": null,
  "fields": {
    "name": "Othello",
    "author": {
      "id": null,
      "name": "Shakespeare"
    }
  }
}
]
""",
        "my_field_thing": """[
{
  "model": "serializers.myfieldthing",
  "pk": null,
  "fields": {
    "name": "XXX-Foo-XXX"
  }
}
]
""",
    }


class XMLSerializerTests(SerializationTests, TestCase):
    serialization_format = "xml"
    expected_data = {
        "embedded_model_field": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serializers.book">
    <field name="name" type="CharField">Othello</field>
    <field name="author" type="JSONField">
      <object model="serializers.book">
        <field name="id" type="BigAutoField"><None></None></field>
        <field name="name" type="CharField">Shakespeare</field>
      </object></field>
  </object>
</django-objects>""",
        "my_field_thing": """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0">
  <object model="serializers.myfieldthing">
    <field name="name" type="CharField">YYY-Foo-YYY</field>
  </object>
</django-objects>""",
    }


class ClassLookupDictTests(SimpleTestCase):
    def test_not_found_in_mapping(self):
        class MyClass:
            pass

        lookup = ClassLookupDict({})
        with self.assertRaisesMessage(KeyError, "Class MyClass not found in mapping."):
            lookup[MyClass()]
