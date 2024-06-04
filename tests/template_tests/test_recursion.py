from django.template import loader
from django.test import SimpleTestCase

context = {
    "items": [
        {
            "name": "foo",
            "items": [],
        },
        {
            "name": "bar",
            "items": [
                {
                    "name": "baz",
                    "items": [],
                },
            ],
        },
    ],
}

expected_result = "(foo)(bar(baz))"


class RecursionTests(SimpleTestCase):
    def test_recursion(self):
        for i in range(3):
            template = loader.get_template(f"recursion/include{i}.html")
            actual_result = "".join(template.render(context).split())
            self.assertEqual(actual_result, expected_result)
