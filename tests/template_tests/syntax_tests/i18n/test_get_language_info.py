# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import SimpleTestCase
from django.utils import translation

from ...utils import setup


class I18nGetLanguageInfoTagTests(SimpleTestCase):
    libraries = {
        'custom': 'template_tests.templatetags.custom',
        'i18n': 'django.templatetags.i18n',
    }

    # retrieving language information
    @setup({'i18n28_2': '{% load i18n %}'
                        '{% get_language_info for "de" as l %}'
                        '{{ l.code }}: {{ l.name }}/{{ l.name_local }} bidi={{ l.bidi }}'})
    def test_i18n28_2(self):
        output = self.engine.render_to_string('i18n28_2')
        self.assertEqual(output, 'de: German/Deutsch bidi=False')

    @setup({'i18n29': '{% load i18n %}'
                      '{% get_language_info for LANGUAGE_CODE as l %}'
                      '{{ l.code }}: {{ l.name }}/{{ l.name_local }} bidi={{ l.bidi }}'})
    def test_i18n29(self):
        output = self.engine.render_to_string('i18n29', {'LANGUAGE_CODE': 'fi'})
        self.assertEqual(output, 'fi: Finnish/suomi bidi=False')

    # Test whitespace in filter arguments
    @setup({'i18n38': '{% load i18n custom %}'
                      '{% get_language_info for "de"|noop:"x y" as l %}'
                      '{{ l.code }}: {{ l.name }}/{{ l.name_local }}/'
                      '{{ l.name_translated }} bidi={{ l.bidi }}'})
    def test_i18n38(self):
        with translation.override('cs'):
            output = self.engine.render_to_string('i18n38')
        self.assertEqual(output, 'de: German/Deutsch/německy bidi=False')
