# coding: utf-8
from __future__ import unicode_literals

from django.test import SimpleTestCase
from django.utils import translation

from ..utils import setup


class I18nTagTests(SimpleTestCase):
    libraries = {
        'custom': 'template_tests.templatetags.custom',
        'i18n': 'django.templatetags.i18n',
    }

    @setup({'i18n10': '{{ bool|yesno:_("yes,no,maybe") }}'})
    def test_i18n10(self):
        """
        translation of a variable with a translated filter
        """
        with translation.override('de'):
            output = self.engine.render_to_string('i18n10', {'bool': True})
        self.assertEqual(output, 'Ja')

    @setup({'i18n11': '{{ bool|yesno:"ja,nein" }}'})
    def test_i18n11(self):
        """
        translation of a variable with a non-translated filter
        """
        output = self.engine.render_to_string('i18n11', {'bool': True})
        self.assertEqual(output, 'ja')

    @setup({'i18n12': '{% load i18n %}'
                      '{% get_available_languages as langs %}{% for lang in langs %}'
                      '{% if lang.0 == "de" %}{{ lang.0 }}{% endif %}{% endfor %}'})
    def test_i18n12(self):
        """
        usage of the get_available_languages tag
        """
        output = self.engine.render_to_string('i18n12')
        self.assertEqual(output, 'de')

    @setup({'i18n13': '{{ _("Password") }}'})
    def test_i18n13(self):
        """
        translation of constant strings
        """
        with translation.override('de'):
            output = self.engine.render_to_string('i18n13')
        self.assertEqual(output, 'Passwort')

    @setup({'i18n14': '{% cycle "foo" _("Password") _(\'Password\') as c %} {% cycle c %} {% cycle c %}'})
    def test_i18n14(self):
        """
        translation of constant strings
        """
        with translation.override('de'):
            output = self.engine.render_to_string('i18n14')
        self.assertEqual(output, 'foo Passwort Passwort')

    @setup({'i18n15': '{{ absent|default:_("Password") }}'})
    def test_i18n15(self):
        """
        translation of constant strings
        """
        with translation.override('de'):
            output = self.engine.render_to_string('i18n15', {'absent': ''})
        self.assertEqual(output, 'Passwort')

    @setup({'i18n16': '{{ _("<") }}'})
    def test_i18n16(self):
        """
        translation of constant strings
        """
        with translation.override('de'):
            output = self.engine.render_to_string('i18n16')
        self.assertEqual(output, '<')

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

    # Test whitespace in filter arguments
    @setup({'i18n38': '{% load i18n custom %}'
                      '{% get_language_info for "de"|noop:"x y" as l %}'
                      '{{ l.code }}: {{ l.name }}/{{ l.name_local }}/'
                      '{{ l.name_translated }} bidi={{ l.bidi }}'})
    def test_i18n38(self):
        with translation.override('cs'):
            output = self.engine.render_to_string('i18n38')
        self.assertEqual(output, 'de: German/Deutsch/německy bidi=False')

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
