import unittest

from django.db import NotSupportedError, connection
from django.db.models import CharField, F, Value
from django.db.models.functions import Cast, JSONArray, JSONObject, Lower
from django.test import TestCase
from django.test.testcases import skipIfDBFeature, skipUnlessDBFeature
from django.utils import timezone

from ..models import Article, Author


@skipUnlessDBFeature("supports_json_field")
class JSONArrayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(name="Ivan Ivanov", alias="iivanov")

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

    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
    def test_explicit_cast(self):
        qs = Author.objects.annotate(
            json_array=JSONArray(Cast("age", CharField()))
        ).values("json_array")
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(qs, [{"json_array": ["30"]}])
        sql = ctx.captured_queries[0]["sql"]
        self.assertIn("::varchar", sql)
        self.assertNotIn("::varchar)::varchar", sql)

    def test_order_by_key(self):
        qs = Author.objects.annotate(arr=JSONArray(F("alias"))).order_by("arr__0")
        self.assertQuerySetEqual(qs, Author.objects.order_by("alias"))

    def test_order_by_nested_key(self):
        qs = Author.objects.annotate(arr=JSONArray(JSONArray(F("alias")))).order_by(
            "-arr__0__0"
        )
        self.assertQuerySetEqual(qs, Author.objects.order_by("-alias"))


@skipIfDBFeature("supports_json_field")
class JSONArrayNotSupportedTests(TestCase):
    def test_not_supported(self):
        msg = "JSONFields are not supported on this database backend."
        with self.assertRaisesMessage(NotSupportedError, msg):
            Author.objects.annotate(json_array=JSONArray()).first()


@skipUnlessDBFeature("has_json_object_function", "supports_json_field")
class JSONArrayObjectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.create(name="Ivan Ivanov", alias="iivanov")

    def test_nested_json_array_object(self):
        obj = Author.objects.annotate(
            json_array=JSONArray(
                JSONObject(
                    name1="name",
                    nested_json_object1=JSONObject(alias1="alias", age1="age"),
                ),
                JSONObject(
                    name2="name",
                    nested_json_object2=JSONObject(alias2="alias", age2="age"),
                ),
            )
        ).first()
        self.assertEqual(
            obj.json_array,
            [
                {
                    "name1": "Ivan Ivanov",
                    "nested_json_object1": {"alias1": "iivanov", "age1": 30},
                },
                {
                    "name2": "Ivan Ivanov",
                    "nested_json_object2": {"alias2": "iivanov", "age2": 30},
                },
            ],
        )

    def test_nested_json_object_array(self):
        obj = Author.objects.annotate(
            json_object=JSONObject(
                name="name",
                nested_json_array=JSONArray(
                    JSONObject(alias1="alias", age1="age"),
                    JSONObject(alias2="alias", age2="age"),
                ),
            )
        ).first()
        self.assertEqual(
            obj.json_object,
            {
                "name": "Ivan Ivanov",
                "nested_json_array": [
                    {"alias1": "iivanov", "age1": 30},
                    {"alias2": "iivanov", "age2": 30},
                ],
            },
        )

    def test_order_by_nested_key(self):
        qs = Author.objects.annotate(
            arr=JSONArray(JSONObject(alias=F("alias")))
        ).order_by("-arr__0__alias")
        self.assertQuerySetEqual(qs, Author.objects.order_by("-alias"))
