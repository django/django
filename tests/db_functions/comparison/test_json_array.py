from django.db import NotSupportedError
from django.db.models import F, Value
from django.db.models.functions import JSONArray, Lower
from django.test import TestCase
from django.test.testcases import skipIfDBFeature, skipUnlessDBFeature
from django.utils import timezone

from ..models import Article, Author


@skipUnlessDBFeature("has_json_object_function")
class JSONArrayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.bulk_create(
            [
                Author(name="Ivan Ivanov", alias="iivanov"),
                Author(name="Bertha Berthy", alias="bberthy"),
            ]
        )

    def test_empty(self):
        obj = Author.objects.annotate(json_array=JSONArray()).first()
        self.assertEqual(obj.json_array, [])

    def test_basic(self):
        obj = Author.objects.annotate(
            json_array=JSONArray(Value("name"), F("name"))
        ).first()
        self.assertEqual(obj.json_array, ["name", "Ivan Ivanov"])

    def test_expressions(self):
        obj = Author.objects.annotate(
            json_array=JSONArray(
                Lower("name"),
                F("alias"),
                F("goes_by"),
                Value(30000.15),
                F("age") * 2,
            )
        ).first()
        self.assertEqual(
            obj.json_array,
            [
                "ivan ivanov",
                "iivanov",
                None,
                30000.15,
                60,
            ],
        )

    def test_nested_json_array(self):
        obj = Author.objects.annotate(
            json_array=JSONArray(
                F("name"),
                JSONArray(F("alias"), F("age")),
            )
        ).first()
        self.assertEqual(
            obj.json_array,
            [
                "Ivan Ivanov",
                ["iivanov", 30],
            ],
        )

    def test_nested_empty_json_array(self):
        obj = Author.objects.annotate(
            json_array=JSONArray(
                F("name"),
                JSONArray(),
            )
        ).first()
        self.assertEqual(
            obj.json_array,
            [
                "Ivan Ivanov",
                [],
            ],
        )

    def test_textfield(self):
        Article.objects.create(
            title="The Title",
            text="x" * 4000,
            written=timezone.now(),
        )
        obj = Article.objects.annotate(json_array=JSONArray(F("text"))).first()
        self.assertEqual(obj.json_array, ["x" * 4000])

    def test_order_by_key(self):
        qs = Author.objects.annotate(arr=JSONArray(F("alias"))).order_by("arr__0")
        self.assertQuerySetEqual(qs, Author.objects.order_by("alias"))

    def test_order_by_nested_key(self):
        qs = Author.objects.annotate(arr=JSONArray(JSONArray(F("alias")))).order_by(
            "-arr__0__0"
        )
        self.assertQuerySetEqual(qs, Author.objects.order_by("-alias"))


@skipIfDBFeature("has_json_object_function")
class JSONObjectNotSupportedTests(TestCase):
    def test_not_supported(self):
        msg = "JSONArray() is not supported on this database backend."
        with self.assertRaisesMessage(NotSupportedError, msg):
            Author.objects.annotate(json_array=JSONArray()).get()
