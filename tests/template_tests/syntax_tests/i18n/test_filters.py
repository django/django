# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import SimpleTestCase
from django.utils import translation

from ...utils import setup


class I18nFiltersTests(SimpleTestCase):
    libraries = {
        'custom': 'template_tests.templatetags.custom',
        'i18n': 'django.templatetags.i18n',
    }

    @setup({'i18n32': '{% load i18n %}{{ "hu"|language_name }} '
                      '{{ "hu"|language_name_local }} {{ "hu"|language_bidi }} '
                      '{{ "hu"|language_name_translated }}'})
    def test_i18n32(self):
        output = self.engine.render_to_string('i18n32')
        self.assertEqual(output, 'Hungarian Magyar False Hungarian')

        with translation.override('cs'):
            output = self.engine.render_to_string('i18n32')
            self.assertEqual(output, 'Hungarian Magyar False maďarsky')

    @setup({'i18n33': '{% load i18n %}'
                      '{{ langcode|language_name }} {{ langcode|language_name_local }} '
                      '{{ langcode|language_bidi }} {{ langcode|language_name_translated }}'})
    def test_i18n33(self):
        output = self.engine.render_to_string('i18n33', {'langcode': 'nl'})
        self.assertEqual(output, 'Dutch Nederlands False Dutch')

        with translation.override('cs'):
            output = self.engine.render_to_string('i18n33', {'langcode': 'nl'})
            self.assertEqual(output, 'Dutch Nederlands False nizozemsky')

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
