from django.template import TemplateSyntaxError
from django.template.defaulttags import WithNode
from django.test import SimpleTestCase

from ..utils import setup


class WithTagTests(SimpleTestCase):

    @setup({'with01': '{% with key=dict.key %}{{ key }}{% endwith %}'})
    def test_with01(self):
        output = self.engine.render_to_string('with01', {'dict': {'key': 50}})
        self.assertEqual(output, '50')

    @setup({'legacywith01': '{% with dict.key as key %}{{ key }}{% endwith %}'})
    def test_legacywith01(self):
        output = self.engine.render_to_string('legacywith01', {'dict': {'key': 50}})
        self.assertEqual(output, '50')

    @setup({'with02': '{{ key }}{% with key=dict.key %}'
                      '{{ key }}-{{ dict.key }}-{{ key }}'
                      '{% endwith %}{{ key }}'})
    def test_with02(self):
        output = self.engine.render_to_string('with02', {'dict': {'key': 50}})
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID50-50-50INVALID')
        else:
            self.assertEqual(output, '50-50-50')

    @setup({'legacywith02': '{{ key }}{% with dict.key as key %}'
                            '{{ key }}-{{ dict.key }}-{{ key }}'
                            '{% endwith %}{{ key }}'})
    def test_legacywith02(self):
        output = self.engine.render_to_string('legacywith02', {'dict': {'key': 50}})
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID50-50-50INVALID')
        else:
            self.assertEqual(output, '50-50-50')

    @setup({'with03': '{% with a=alpha b=beta %}{{ a }}{{ b }}{% endwith %}'})
    def test_with03(self):
        output = self.engine.render_to_string('with03', {'alpha': 'A', 'beta': 'B'})
        self.assertEqual(output, 'AB')

    @setup({'with-error01': '{% with dict.key xx key %}{{ key }}{% endwith %}'})
    def test_with_error01(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('with-error01', {'dict': {'key': 50}})

    @setup({'with-error02': '{% with dict.key as %}{{ key }}{% endwith %}'})
    def test_with_error02(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('with-error02', {'dict': {'key': 50}})


class WithNodeTests(SimpleTestCase):
    def test_repr(self):
        node = WithNode(nodelist=[], name='a', var='dict.key')
        self.assertEqual(repr(node), '<WithNode>')
