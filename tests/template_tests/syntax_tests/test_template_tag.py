from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class TemplateTagTests(SimpleTestCase):

    @setup({'templatetag01': '{% templatetag openblock %}'})
    def test_templatetag01(self):
        output = self.engine.render_to_string('templatetag01')
        self.assertEqual(output, '{%')

    @setup({'templatetag02': '{% templatetag closeblock %}'})
    def test_templatetag02(self):
        output = self.engine.render_to_string('templatetag02')
        self.assertEqual(output, '%}')

    @setup({'templatetag03': '{% templatetag openvariable %}'})
    def test_templatetag03(self):
        output = self.engine.render_to_string('templatetag03')
        self.assertEqual(output, '{{')

    @setup({'templatetag04': '{% templatetag closevariable %}'})
    def test_templatetag04(self):
        output = self.engine.render_to_string('templatetag04')
        self.assertEqual(output, '}}')

    @setup({'templatetag05': '{% templatetag %}'})
    def test_templatetag05(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('templatetag05')

    @setup({'templatetag06': '{% templatetag foo %}'})
    def test_templatetag06(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('templatetag06')

    @setup({'templatetag07': '{% templatetag openbrace %}'})
    def test_templatetag07(self):
        output = self.engine.render_to_string('templatetag07')
        self.assertEqual(output, '{')

    @setup({'templatetag08': '{% templatetag closebrace %}'})
    def test_templatetag08(self):
        output = self.engine.render_to_string('templatetag08')
        self.assertEqual(output, '}')

    @setup({'templatetag09': '{% templatetag openbrace %}{% templatetag openbrace %}'})
    def test_templatetag09(self):
        output = self.engine.render_to_string('templatetag09')
        self.assertEqual(output, '{{')

    @setup({'templatetag10': '{% templatetag closebrace %}{% templatetag closebrace %}'})
    def test_templatetag10(self):
        output = self.engine.render_to_string('templatetag10')
        self.assertEqual(output, '}}')

    @setup({'templatetag11': '{% templatetag opencomment %}'})
    def test_templatetag11(self):
        output = self.engine.render_to_string('templatetag11')
        self.assertEqual(output, '{#')

    @setup({'templatetag12': '{% templatetag closecomment %}'})
    def test_templatetag12(self):
        output = self.engine.render_to_string('templatetag12')
        self.assertEqual(output, '#}')
