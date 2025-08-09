from django.db import NotSupportedError
from django.db.models import F, Value
from django.db.models.functions import JSONArray
from django.db.models.functions.json import _JSONArrayConcat as JSONConcat
from django.test import TestCase
from django.test.testcases import skipIfDBFeature, skipUnlessDBFeature

from ..models import Author


@skipUnlessDBFeature("supports_json_array_concat")
class JSONArrayConcatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.bulk_create(
            [
                Author(name="Ivan Ivanov", alias="iivanov"),
            ]
        )

    def test_invalid(self):
        msg = "_JSONArrayConcat must take at least two expressions"
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(json=JSONConcat()).first()
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(json=JSONConcat(JSONArray(F("name")))).first()

    def test_simple_array(self):
        obj = Author.objects.annotate(
            arr=JSONConcat(
                JSONArray("name"),
                JSONArray("alias"),
            )
        ).first()
        self.assertEqual(obj.arr, ["Ivan Ivanov", "iivanov"])

    def test_array_and_null(self):
        obj = Author.objects.annotate(
            json=JSONConcat(JSONArray("name"), Value(None))
        ).first()
        self.assertEqual(obj.json, None)

    def test_duplicates_preserved(self):
        obj = Author.objects.annotate(
            arr=JSONConcat(
                JSONArray("name"),
                JSONArray("name"),
            )
        ).first()
        self.assertEqual(obj.arr, ["Ivan Ivanov", "Ivan Ivanov"])


@skipIfDBFeature("has_json_object_function")
class JSONArrayConcatNotSupportedTests(TestCase):
    def test_not_supported(self):
        msg = "Concatenating JSON arrays is not supported on this database backend."
        with self.assertRaisesMessage(NotSupportedError, msg):
            Author.objects.annotate(
                arr=JSONConcat(
                    JSONArray("name"),
                    JSONArray("alias"),
                )
            ).first()
