from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class FirstOfTagTests(SimpleTestCase):
    @setup({"firstof01": "{% firstof a b c %}"})
    def test_firstof01(self):
        output = self.engine.render_to_string("firstof01", {"a": 0, "c": 0, "b": 0})
        self.assertEqual(output, "")

    @setup({"firstof02": "{% firstof a b c %}"})
    def test_firstof02(self):
        output = self.engine.render_to_string("firstof02", {"a": 1, "c": 0, "b": 0})
        self.assertEqual(output, "1")

    @setup({"firstof03": "{% firstof a b c %}"})
    def test_firstof03(self):
        output = self.engine.render_to_string("firstof03", {"a": 0, "c": 0, "b": 2})
        self.assertEqual(output, "2")

    @setup({"firstof04": "{% firstof a b c %}"})
    def test_firstof04(self):
        output = self.engine.render_to_string("firstof04", {"a": 0, "c": 3, "b": 0})
        self.assertEqual(output, "3")

    @setup({"firstof05": "{% firstof a b c %}"})
    def test_firstof05(self):
        output = self.engine.render_to_string("firstof05", {"a": 1, "c": 3, "b": 2})
        self.assertEqual(output, "1")

    @setup({"firstof06": "{% firstof a b c %}"})
    def test_firstof06(self):
        output = self.engine.render_to_string("firstof06", {"c": 3, "b": 0})
        self.assertEqual(output, "3")

    @setup({"firstof07": '{% firstof a b "c" %}'})
    def test_firstof07(self):
        output = self.engine.render_to_string("firstof07", {"a": 0})
        self.assertEqual(output, "c")

    @setup({"firstof08": '{% firstof a b "c and d" %}'})
    def test_firstof08(self):
        output = self.engine.render_to_string("firstof08", {"a": 0, "b": 0})
        self.assertEqual(output, "c and d")

    @setup({"firstof09": "{% firstof %}"})
    def test_firstof09(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template("firstof09")

    @setup({"firstof10": "{% firstof a %}"})
    def test_firstof10(self):
        output = self.engine.render_to_string("firstof10", {"a": "<"})
        self.assertEqual(output, "&lt;")

    @setup({"firstof11": "{% firstof a b %}"})
    def test_firstof11(self):
        output = self.engine.render_to_string("firstof11", {"a": "<", "b": ">"})
        self.assertEqual(output, "&lt;")

    @setup({"firstof12": "{% firstof a b %}"})
    def test_firstof12(self):
        output = self.engine.render_to_string("firstof12", {"a": "", "b": ">"})
        self.assertEqual(output, "&gt;")

    @setup({"firstof13": "{% autoescape off %}{% firstof a %}{% endautoescape %}"})
    def test_firstof13(self):
        output = self.engine.render_to_string("firstof13", {"a": "<"})
        self.assertEqual(output, "<")

    @setup({"firstof14": "{% firstof a|safe b %}"})
    def test_firstof14(self):
        output = self.engine.render_to_string("firstof14", {"a": "<"})
        self.assertEqual(output, "<")

    @setup({"firstof15": "{% firstof a b c as myvar %}"})
    def test_firstof15(self):
        ctx = {"a": 0, "b": 2, "c": 3}
        output = self.engine.render_to_string("firstof15", ctx)
        self.assertEqual(ctx["myvar"], "2")
        self.assertEqual(output, "")

    @setup({"firstof16": "{% firstof a b c as myvar %}"})
    def test_all_false_arguments_asvar(self):
        ctx = {"a": 0, "b": 0, "c": 0}
        output = self.engine.render_to_string("firstof16", ctx)
        self.assertEqual(ctx["myvar"], "")
        self.assertEqual(output, "")
