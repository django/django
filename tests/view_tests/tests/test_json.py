import json

from django.test import SimpleTestCase, override_settings


@override_settings(ROOT_URLCONF="view_tests.generic_urls")
class JsonResponseTests(SimpleTestCase):
    def test_json_response(self):
        response = self.client.get("/json/response/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(
            json.loads(response.text),
            {
                "a": [1, 2, 3],
                "foo": {"bar": "baz"},
                "timestamp": "2013-05-19T20:00:00",
                "value": "3.14",
            },
        )
