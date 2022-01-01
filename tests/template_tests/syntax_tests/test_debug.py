from django.contrib.auth.models import Group
from django.test import SimpleTestCase, override_settings

from ..utils import setup


@override_settings(DEBUG=True)
class DebugTests(SimpleTestCase):

    @override_settings(DEBUG=False)
    @setup({'non_debug': '{% debug %}'})
    def test_non_debug(self):
        output = self.engine.render_to_string('non_debug', {})
        self.assertEqual(output, '')

    @setup({'modules': '{% debug %}'})
    def test_modules(self):
        output = self.engine.render_to_string('modules', {})
        self.assertIn(
            '&#39;django&#39;: &lt;module &#39;django&#39; ',
            output,
        )

    @setup({'plain': '{% debug %}'})
    def test_plain(self):
        output = self.engine.render_to_string('plain', {'a': 1})
        self.assertTrue(output.startswith(
            '{&#39;a&#39;: 1}'
            '{&#39;False&#39;: False, &#39;None&#39;: None, '
            '&#39;True&#39;: True}\n\n{'
        ))

    @setup({'non_ascii': '{% debug %}'})
    def test_non_ascii(self):
        group = Group(name="清風")
        output = self.engine.render_to_string('non_ascii', {'group': group})
        self.assertTrue(output.startswith(
            '{&#39;group&#39;: &lt;Group: 清風&gt;}'
        ))

    @setup({'script': '{% debug %}'})
    def test_script(self):
        output = self.engine.render_to_string('script', {'frag': '<script>'})
        self.assertTrue(output.startswith(
            '{&#39;frag&#39;: &#39;&lt;script&gt;&#39;}'
        ))
