from django.template.defaultfilters import force_escape
from django.test import SimpleTestCase
from django.utils.safestring import SafeData

from ..utils import setup


class ForceEscapeTests(SimpleTestCase):
    """
    Force_escape is applied immediately. It can be used to provide
    double-escaping, for example.
    """

    @setup({'force-escape01': '{% autoescape off %}{{ a|force_escape }}{% endautoescape %}'})
    def test_force_escape01(self):
        output = self.engine.render_to_string('force-escape01', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape02': '{{ a|force_escape }}'})
    def test_force_escape02(self):
        output = self.engine.render_to_string('force-escape02', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape03': '{% autoescape off %}{{ a|force_escape|force_escape }}{% endautoescape %}'})
    def test_force_escape03(self):
        output = self.engine.render_to_string('force-escape03', {"a": "x&y"})
        self.assertEqual(output, "x&amp;amp;y")

    @setup({'force-escape04': '{{ a|force_escape|force_escape }}'})
    def test_force_escape04(self):
        output = self.engine.render_to_string('force-escape04', {"a": "x&y"})
        self.assertEqual(output, "x&amp;amp;y")

    # Because the result of force_escape is "safe", an additional
    # escape filter has no effect.
    @setup({'force-escape05': '{% autoescape off %}{{ a|force_escape|escape }}{% endautoescape %}'})
    def test_force_escape05(self):
        output = self.engine.render_to_string('force-escape05', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape06': '{{ a|force_escape|escape }}'})
    def test_force_escape06(self):
        output = self.engine.render_to_string('force-escape06', {"a": "x&y"})
        self.assertEqual(output, "x&amp;y")

    @setup({'force-escape07': '{% autoescape off %}{{ a|escape|force_escape }}{% endautoescape %}'})
    def test_force_escape07(self):
        output = self.engine.render_to_string('force-escape07', {"a": "x&y"})
        self.assertEqual(output, "x&amp;amp;y")

    @setup({'force-escape08': '{{ a|escape|force_escape }}'})
    def test_force_escape08(self):
        output = self.engine.render_to_string('force-escape08', {"a": "x&y"})
        self.assertEqual(output, "x&amp;amp;y")


class FunctionTests(SimpleTestCase):

    def test_escape(self):
        escaped = force_escape('<some html & special characters > here')
        self.assertEqual(escaped, '&lt;some html &amp; special characters &gt; here')
        self.assertIsInstance(escaped, SafeData)

    def test_unicode(self):
        self.assertEqual(
            force_escape('<some html & special characters > here ĐÅ€£'),
            '&lt;some html &amp; special characters &gt; here \u0110\xc5\u20ac\xa3',
        )
