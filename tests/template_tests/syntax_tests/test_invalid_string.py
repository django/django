from django.conf import settings
from django.test import SimpleTestCase

from ..utils import render, setup


class InvalidStringTests(SimpleTestCase):

    @setup({'invalidstr01': '{{ var|default:"Foo" }}'})
    def test_invalidstr01(self):
        output = render('invalidstr01')
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, 'Foo')

    @setup({'invalidstr02': '{{ var|default_if_none:"Foo" }}'})
    def test_invalidstr02(self):
        output = render('invalidstr02')
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'invalidstr03': '{% for v in var %}({{ v }}){% endfor %}'})
    def test_invalidstr03(self):
        output = render('invalidstr03')
        self.assertEqual(output, '')

    @setup({'invalidstr04': '{% if var %}Yes{% else %}No{% endif %}'})
    def test_invalidstr04(self):
        output = render('invalidstr04')
        self.assertEqual(output, 'No')

    @setup({'invalidstr04_2': '{% if var|default:"Foo" %}Yes{% else %}No{% endif %}'})
    def test_invalidstr04_2(self):
        output = render('invalidstr04_2')
        self.assertEqual(output, 'Yes')

    @setup({'invalidstr05': '{{ var }}'})
    def test_invalidstr05(self):
        output = render('invalidstr05')
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'invalidstr06': '{{ var.prop }}'})
    def test_invalidstr06(self):
        output = render('invalidstr06')
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')

    @setup({'invalidstr07': '{% load i18n %}{% blocktrans %}{{ var }}{% endblocktrans %}'})
    def test_invalidstr07(self):
        output = render('invalidstr07')
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')
