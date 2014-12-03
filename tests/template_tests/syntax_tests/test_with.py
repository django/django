from django.conf import settings
from django.template.base import TemplateSyntaxError
from django.test import SimpleTestCase

from .utils import render, setup


class WithTagTests(SimpleTestCase):

    @setup({'with01': '{% with key=dict.key %}{{ key }}{% endwith %}'})
    def test_with01(self):
        output = render('with01', {'dict': {'key': 50}})
        self.assertEqual(output, '50')

    @setup({'legacywith01': '{% with dict.key as key %}{{ key }}{% endwith %}'})
    def test_legacywith01(self):
        output = render('legacywith01', {'dict': {'key': 50}})
        self.assertEqual(output, '50')

    @setup({'with02': '{{ key }}{% with key=dict.key %}'
                      '{{ key }}-{{ dict.key }}-{{ key }}'
                      '{% endwith %}{{ key }}'})
    def test_with02(self):
        output = render('with02', {'dict': {'key': 50}})
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID50-50-50INVALID')
        else:
            self.assertEqual(output, '50-50-50')

    @setup({'legacywith02': '{{ key }}{% with dict.key as key %}'
                            '{{ key }}-{{ dict.key }}-{{ key }}'
                            '{% endwith %}{{ key }}'})
    def test_legacywith02(self):
        output = render('legacywith02', {'dict': {'key': 50}})
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID50-50-50INVALID')
        else:
            self.assertEqual(output, '50-50-50')

    @setup({'with03': '{% with a=alpha b=beta %}{{ a }}{{ b }}{% endwith %}'})
    def test_with03(self):
        output = render('with03', {'alpha': 'A', 'beta': 'B'})
        self.assertEqual(output, 'AB')

    @setup({'with-error01': '{% with dict.key xx key %}{{ key }}{% endwith %}'})
    def test_with_error01(self):
        with self.assertRaises(TemplateSyntaxError):
            render('with-error01', {'dict': {'key': 50}})

    @setup({'with-error02': '{% with dict.key as %}{{ key }}{% endwith %}'})
    def test_with_error02(self):
        with self.assertRaises(TemplateSyntaxError):
            render('with-error02', {'dict': {'key': 50}})
