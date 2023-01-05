from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class FilterTagTests(SimpleTestCase):
    @setup({"filter01": "{% filter upper %}{% endfilter %}"})
    def test_filter01(self):
        output = self.engine.render_to_string("filter01")
        self.assertEqual(output, "")

    @setup({"filter02": "{% filter upper %}django{% endfilter %}"})
    def test_filter02(self):
        output = self.engine.render_to_string("filter02")
        self.assertEqual(output, "DJANGO")

    @setup({"filter03": "{% filter upper|lower %}django{% endfilter %}"})
    def test_filter03(self):
        output = self.engine.render_to_string("filter03")
        self.assertEqual(output, "django")

    @setup({"filter04": "{% filter cut:remove %}djangospam{% endfilter %}"})
    def test_filter04(self):
        output = self.engine.render_to_string("filter04", {"remove": "spam"})
        self.assertEqual(output, "django")

    @setup({"filter05": "{% filter safe %}fail{% endfilter %}"})
    def test_filter05(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("filter05")

    @setup({"filter05bis": "{% filter upper|safe %}fail{% endfilter %}"})
    def test_filter05bis(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("filter05bis")

    @setup({"filter06": "{% filter escape %}fail{% endfilter %}"})
    def test_filter06(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("filter06")

    @setup({"filter06bis": "{% filter upper|escape %}fail{% endfilter %}"})
    def test_filter06bis(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("filter06bis")
