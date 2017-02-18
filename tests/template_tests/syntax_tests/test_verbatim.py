from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class VerbatimTagTests(SimpleTestCase):

    @setup({'verbatim-tag01': '{% verbatim %}{{bare   }}{% endverbatim %}'})
    def test_verbatim_tag01(self):
        output = self.engine.render_to_string('verbatim-tag01')
        self.assertEqual(output, '{{bare   }}')

    @setup({'verbatim-tag02': '{% verbatim %}{% endif %}{% endverbatim %}'})
    def test_verbatim_tag02(self):
        output = self.engine.render_to_string('verbatim-tag02')
        self.assertEqual(output, '{% endif %}')

    @setup({'verbatim-tag03': '{% verbatim %}It\'s the {% verbatim %} tag{% endverbatim %}'})
    def test_verbatim_tag03(self):
        output = self.engine.render_to_string('verbatim-tag03')
        self.assertEqual(output, 'It\'s the {% verbatim %} tag')

    @setup({'verbatim-tag04': '{% verbatim %}{% verbatim %}{% endverbatim %}{% endverbatim %}'})
    def test_verbatim_tag04(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('verbatim-tag04')

    @setup({'verbatim-tag05': '{% verbatim %}{% endverbatim %}{% verbatim %}{% endverbatim %}'})
    def test_verbatim_tag05(self):
        output = self.engine.render_to_string('verbatim-tag05')
        self.assertEqual(output, '')

    @setup({'verbatim-tag06': '{% verbatim special %}'
                              'Don\'t {% endverbatim %} just yet{% endverbatim special %}'})
    def test_verbatim_tag06(self):
        output = self.engine.render_to_string('verbatim-tag06')
        self.assertEqual(output, 'Don\'t {% endverbatim %} just yet')
