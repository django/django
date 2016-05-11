import warnings

from django.test import SimpleTestCase, ignore_warnings
from django.test.utils import reset_warning_registry
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.safestring import mark_safe

from ..utils import setup


class ChainingTests(SimpleTestCase):
    """
    Chaining safeness-preserving filters should not alter the safe status.
    """

    @setup({'chaining01': '{{ a|capfirst|center:"7" }}.{{ b|capfirst|center:"7" }}'})
    def test_chaining01(self):
        output = self.engine.render_to_string('chaining01', {'a': 'a < b', 'b': mark_safe('a < b')})
        self.assertEqual(output, ' A &lt; b . A < b ')

    @setup({
        'chaining02':
        '{% autoescape off %}{{ a|capfirst|center:"7" }}.{{ b|capfirst|center:"7" }}{% endautoescape %}'
    })
    def test_chaining02(self):
        output = self.engine.render_to_string('chaining02', {'a': 'a < b', 'b': mark_safe('a < b')})
        self.assertEqual(output, ' A < b . A < b ')

    # Using a filter that forces a string back to unsafe:
    @setup({'chaining03': '{{ a|cut:"b"|capfirst }}.{{ b|cut:"b"|capfirst }}'})
    def test_chaining03(self):
        output = self.engine.render_to_string('chaining03', {'a': 'a < b', 'b': mark_safe('a < b')})
        self.assertEqual(output, 'A &lt; .A < ')

    @setup({
        'chaining04': '{% autoescape off %}{{ a|cut:"b"|capfirst }}.{{ b|cut:"b"|capfirst }}{% endautoescape %}'
    })
    def test_chaining04(self):
        output = self.engine.render_to_string('chaining04', {'a': 'a < b', 'b': mark_safe('a < b')})
        self.assertEqual(output, 'A < .A < ')

    # Using a filter that forces safeness does not lead to double-escaping
    @setup({'chaining05': '{{ a|escape|capfirst }}'})
    def test_chaining05(self):
        reset_warning_registry()
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            output = self.engine.render_to_string('chaining05', {'a': 'a < b'})
            self.assertEqual(output, 'A &lt; b')

        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            "escape isn't the last filter in ['escape_filter', 'capfirst'] and "
            "will be applied immediately in Django 2.0 so the output may change."
        )

    @ignore_warnings(category=RemovedInDjango20Warning)
    @setup({'chaining06': '{% autoescape off %}{{ a|escape|capfirst }}{% endautoescape %}'})
    def test_chaining06(self):
        output = self.engine.render_to_string('chaining06', {'a': 'a < b'})
        self.assertEqual(output, 'A &lt; b')

    # Force to safe, then back (also showing why using force_escape too
    # early in a chain can lead to unexpected results).
    @setup({'chaining07': '{{ a|force_escape|cut:";" }}'})
    def test_chaining07(self):
        output = self.engine.render_to_string('chaining07', {'a': 'a < b'})
        self.assertEqual(output, 'a &amp;lt b')

    @setup({'chaining08': '{% autoescape off %}{{ a|force_escape|cut:";" }}{% endautoescape %}'})
    def test_chaining08(self):
        output = self.engine.render_to_string('chaining08', {'a': 'a < b'})
        self.assertEqual(output, 'a &lt b')

    @setup({'chaining09': '{{ a|cut:";"|force_escape }}'})
    def test_chaining09(self):
        output = self.engine.render_to_string('chaining09', {'a': 'a < b'})
        self.assertEqual(output, 'a &lt; b')

    @setup({'chaining10': '{% autoescape off %}{{ a|cut:";"|force_escape }}{% endautoescape %}'})
    def test_chaining10(self):
        output = self.engine.render_to_string('chaining10', {'a': 'a < b'})
        self.assertEqual(output, 'a &lt; b')

    @setup({'chaining11': '{{ a|cut:"b"|safe }}'})
    def test_chaining11(self):
        output = self.engine.render_to_string('chaining11', {'a': 'a < b'})
        self.assertEqual(output, 'a < ')

    @setup({'chaining12': '{% autoescape off %}{{ a|cut:"b"|safe }}{% endautoescape %}'})
    def test_chaining12(self):
        output = self.engine.render_to_string('chaining12', {'a': 'a < b'})
        self.assertEqual(output, 'a < ')

    @setup({'chaining13': '{{ a|safe|force_escape }}'})
    def test_chaining13(self):
        output = self.engine.render_to_string('chaining13', {"a": "a < b"})
        self.assertEqual(output, 'a &lt; b')

    @setup({'chaining14': '{% autoescape off %}{{ a|safe|force_escape }}{% endautoescape %}'})
    def test_chaining14(self):
        output = self.engine.render_to_string('chaining14', {"a": "a < b"})
        self.assertEqual(output, 'a &lt; b')
