from django.db.models import F
from django.db.models.functions import JSONArray, JSONObject
from django.test import TestCase
from django.test.testcases import skipUnlessDBFeature

from ..models import Author


@skipUnlessDBFeature("has_json_object_function")
class JSONArrayObjectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Author.objects.bulk_create(
            [
                Author(name="Ivan Ivanov", alias="iivanov"),
                Author(name="Bertha Berthy", alias="bberthy"),
            ]
        )

    def test_nested_json_array_object(self):
        obj = Author.objects.annotate(
            json_array=JSONArray(
                JSONObject(
                    name1="name",
                    nested_json_object1=JSONObject(
                        alias1="alias",
                        age1="age",
                    ),
                ),
                JSONObject(
                    name2="name",
                    nested_json_object2=JSONObject(
                        alias2="alias",
                        age2="age",
                    ),
                ),
            )
        ).first()
        self.assertEqual(
            obj.json_array,
            [
                {
                    "name1": "Ivan Ivanov",
                    "nested_json_object1": {
                        "alias1": "iivanov",
                        "age1": 30,
                    },
                },
                {
                    "name2": "Ivan Ivanov",
                    "nested_json_object2": {
                        "alias2": "iivanov",
                        "age2": 30,
                    },
                },
            ],
        )

    def test_nested_json_object_array(self):
        obj = Author.objects.annotate(
            json_object=JSONObject(
                name="name",
                nested_json_array=JSONArray(
                    JSONObject(
                        alias1="alias",
                        age1="age",
                    ),
                    JSONObject(
                        alias2="alias",
                        age2="age",
                    ),
                ),
            )
        ).first()
        self.assertEqual(
            obj.json_object,
            {
                "name": "Ivan Ivanov",
                "nested_json_array": [
                    {
                        "alias1": "iivanov",
                        "age1": 30,
                    },
                    {
                        "alias2": "iivanov",
                        "age2": 30,
                    },
                ],
            },
        )

    def test_order_by_nested_key(self):
        qs = Author.objects.annotate(
            arr=JSONArray(JSONObject(alias=F("alias")))
        ).order_by("-arr__0__alias")
        self.assertQuerySetEqual(qs, Author.objects.order_by("-alias"))
