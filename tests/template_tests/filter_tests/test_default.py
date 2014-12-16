from django.test import SimpleTestCase
from django.utils.safestring import mark_safe

from ..utils import render, setup


class DefaultTests(SimpleTestCase):
    """
    Literal string arguments to the default filter are always treated as
    safe strings, regardless of the auto-escaping state.

    Note: we have to use {"a": ""} here, otherwise the invalid template
    variable string interferes with the test result.
    """

    @setup({'default01': '{{ a|default:"x<" }}'})
    def test_default01(self):
        output = render('default01', {"a": ""})
        self.assertEqual(output, "x<")

    @setup({'default02': '{% autoescape off %}{{ a|default:"x<" }}{% endautoescape %}'})
    def test_default02(self):
        output = render('default02', {"a": ""})
        self.assertEqual(output, "x<")

    @setup({'default03': '{{ a|default:"x<" }}'})
    def test_default03(self):
        output = render('default03', {"a": mark_safe("x>")})
        self.assertEqual(output, "x>")

    @setup({'default04': '{% autoescape off %}{{ a|default:"x<" }}{% endautoescape %}'})
    def test_default04(self):
        output = render('default04', {"a": mark_safe("x>")})
        self.assertEqual(output, "x>")


class DefaultIfNoneTests(SimpleTestCase):

    @setup({'default_if_none01': '{{ a|default:"x<" }}'})
    def test_default_if_none01(self):
        output = render('default_if_none01', {"a": None})
        self.assertEqual(output, "x<")

    @setup({'default_if_none02': '{% autoescape off %}{{ a|default:"x<" }}{% endautoescape %}'})
    def test_default_if_none02(self):
        output = render('default_if_none02', {"a": None})
        self.assertEqual(output, "x<")
