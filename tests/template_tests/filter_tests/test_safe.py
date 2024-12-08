from django.test import SimpleTestCase

from ..utils import setup


class SafeTests(SimpleTestCase):
    @setup({"safe01": "{{ a }} -- {{ a|safe }}"})
    def test_safe01(self):
        output = self.engine.render_to_string("safe01", {"a": "<b>hello</b>"})
        self.assertEqual(output, "&lt;b&gt;hello&lt;/b&gt; -- <b>hello</b>")

    @setup({"safe02": "{% autoescape off %}{{ a }} -- {{ a|safe }}{% endautoescape %}"})
    def test_safe02(self):
        output = self.engine.render_to_string("safe02", {"a": "<b>hello</b>"})
        self.assertEqual(output, "<b>hello</b> -- <b>hello</b>")
