from django.test import SimpleTestCase

from ..utils import render, setup


class ForceEscapeTests(SimpleTestCase):
    """
    Force_escape is applied immediately. It can be used to provide
    double-escaping, for example.
    """

    @setup({'force-escape01': '{% autoescape off %}{{ a|force_escape }}{% endautoescape %}'})
    def test_force_escape01(self):
        output = render('force-escape01', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape02': '{{ a|force_escape }}'})
    def test_force_escape02(self):
        output = render('force-escape02', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape03': '{% autoescape off %}{{ a|force_escape|force_escape }}{% endautoescape %}'})
    def test_force_escape03(self):
        output = render('force-escape03', {"a": "x&y"})
        self.assertEqual(output, "x&amp;amp;y")

    @setup({'force-escape04': '{{ a|force_escape|force_escape }}'})
    def test_force_escape04(self):
        output = render('force-escape04', {"a": "x&y"})
        self.assertEqual(output, "x&amp;amp;y")

    # Because the result of force_escape is "safe", an additional
    # escape filter has no effect.
    @setup({'force-escape05': '{% autoescape off %}{{ a|force_escape|escape }}{% endautoescape %}'})
    def test_force_escape05(self):
        output = render('force-escape05', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape06': '{{ a|force_escape|escape }}'})
    def test_force_escape06(self):
        output = render('force-escape06', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape07': '{% autoescape off %}{{ a|escape|force_escape }}{% endautoescape %}'})
    def test_force_escape07(self):
        output = render('force-escape07', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape08': '{{ a|escape|force_escape }}'})
    def test_force_escape08(self):
        output = render('force-escape08', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")
