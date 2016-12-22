# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import SimpleTestCase
from django.utils import translation

from ...utils import setup


class GetLanguageInfoListTests(SimpleTestCase):
    libraries = {
        'custom': 'template_tests.templatetags.custom',
        'i18n': 'django.templatetags.i18n',
    }

    @setup({'i18n30': '{% load i18n %}'
                      '{% get_language_info_list for langcodes as langs %}'
                      '{% for l in langs %}{{ l.code }}: {{ l.name }}/'
                      '{{ l.name_local }} bidi={{ l.bidi }}; {% endfor %}'})
    def test_i18n30(self):
        output = self.engine.render_to_string('i18n30', {'langcodes': ['it', 'no']})
        self.assertEqual(output, 'it: Italian/italiano bidi=False; no: Norwegian/norsk bidi=False; ')

    @setup({'i18n31': '{% load i18n %}'
                      '{% get_language_info_list for langcodes as langs %}'
                      '{% for l in langs %}{{ l.code }}: {{ l.name }}/'
                      '{{ l.name_local }} bidi={{ l.bidi }}; {% endfor %}'})
    def test_i18n31(self):
        output = self.engine.render_to_string('i18n31', {'langcodes': (('sl', 'Slovenian'), ('fa', 'Persian'))})
        self.assertEqual(
            output,
            'sl: Slovenian/Sloven\u0161\u010dina bidi=False; '
            'fa: Persian/\u0641\u0627\u0631\u0633\u06cc bidi=True; '
        )

    @setup({'i18n38_2': '{% load i18n custom %}'
                        '{% get_language_info_list for langcodes|noop:"x y" as langs %}'
                        '{% for l in langs %}{{ l.code }}: {{ l.name }}/'
                        '{{ l.name_local }}/{{ l.name_translated }} '
                        'bidi={{ l.bidi }}; {% endfor %}'})
    def test_i18n38_2(self):
        with translation.override('cs'):
            output = self.engine.render_to_string('i18n38_2', {'langcodes': ['it', 'fr']})
        self.assertEqual(
            output,
            'it: Italian/italiano/italsky bidi=False; '
            'fr: French/français/francouzsky bidi=False; '
        )
