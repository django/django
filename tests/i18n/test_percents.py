# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.template import Context, Template
from django.test import SimpleTestCase, override_settings
from django.utils._os import upath
from django.utils.encoding import force_text
from django.utils.translation import activate, get_language, trans_real

from .test_extraction import ExtractorTests

SAMPLEPROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(upath(__file__))), 'sampleproject')
SAMPLEPROJECT_LOCALE = os.path.join(SAMPLEPROJECT_DIR, 'locale')


@override_settings(LOCALE_PATHS=[SAMPLEPROJECT_LOCALE])
class FrenchTestCase(SimpleTestCase):
    """Tests using the French translations of the sampleproject."""

    PO_FILE = os.path.join(SAMPLEPROJECT_LOCALE, 'fr', 'LC_MESSAGES', 'django.po')

    def setUp(self):
        self._language = get_language()
        self._translations = trans_real._translations
        activate('fr')

    def tearDown(self):
        trans_real._translations = self._translations
        activate(self._language)


class ExtractingStringsWithPercentSigns(FrenchTestCase, ExtractorTests):
    """
    Tests the extracted string found in the gettext catalog.

    Ensures that percent signs are python formatted.

    These tests should all have an analogous translation tests below, ensuring
    the python formatting does not persist through to a rendered template.
    """

    def setUp(self):
        super(ExtractingStringsWithPercentSigns, self).setUp()
        with open(self.PO_FILE, 'r') as fp:
            self.po_contents = force_text(fp.read())

    def test_trans_tag_with_percent_symbol_at_the_end(self):
        self.assertMsgId('Literal with a percent symbol at the end %%', self.po_contents)

    def test_trans_tag_with_percent_symbol_in_the_middle(self):
        self.assertMsgId('Literal with a percent %% symbol in the middle', self.po_contents)
        self.assertMsgId('It is 100%%', self.po_contents)

    def test_trans_tag_with_string_that_look_like_fmt_spec(self):
        self.assertMsgId('Looks like a str fmt spec %%s but should not be interpreted as such', self.po_contents)
        self.assertMsgId('Looks like a str fmt spec %% o but should not be interpreted as such', self.po_contents)

    def test_adds_python_format_to_all_percent_signs(self):
        self.assertMsgId('1 percent sign %%, 2 percent signs %%%%, 3 percent signs %%%%%%', self.po_contents)
        self.assertMsgId('%(name)s says: 1 percent sign %%, 2 percent signs %%%%', self.po_contents)


class RenderingTemplatesWithPercentSigns(FrenchTestCase):
    """
    Test rendering of templates that use percent signs.

    Ensures both trans and blocktrans tags behave consistently.

    Refs #11240, #11966, #24257
    """

    def test_translates_with_a_percent_symbol_at_the_end(self):
        expected = 'Littérale avec un symbole de pour cent à la fin %'

        trans_tpl = Template('{% load i18n %}{% trans "Literal with a percent symbol at the end %" %}')
        self.assertEqual(trans_tpl.render(Context({})), expected)

        block_tpl = Template(
            '{% load i18n %}{% blocktrans %}Literal with a percent symbol at '
            'the end %{% endblocktrans %}'
        )
        self.assertEqual(block_tpl.render(Context({})), expected)

    def test_translates_with_percent_symbol_in_the_middle(self):
        expected = 'Pour cent littérale % avec un symbole au milieu'

        trans_tpl = Template('{% load i18n %}{% trans "Literal with a percent % symbol in the middle" %}')
        self.assertEqual(trans_tpl.render(Context({})), expected)

        block_tpl = Template(
            '{% load i18n %}{% blocktrans %}Literal with a percent % symbol '
            'in the middle{% endblocktrans %}'
        )
        self.assertEqual(block_tpl.render(Context({})), expected)

    def test_translates_with_percent_symbol_using_context(self):
        trans_tpl = Template('{% load i18n %}{% trans "It is 100%" %}')
        self.assertEqual(trans_tpl.render(Context({})), 'Il est de 100%')
        trans_tpl = Template('{% load i18n %}{% trans "It is 100%" context "female" %}')
        self.assertEqual(trans_tpl.render(Context({})), 'Elle est de 100%')

        block_tpl = Template('{% load i18n %}{% blocktrans %}It is 100%{% endblocktrans %}')
        self.assertEqual(block_tpl.render(Context({})), 'Il est de 100%')
        block_tpl = Template('{% load i18n %}{% blocktrans context "female" %}It is 100%{% endblocktrans %}')
        self.assertEqual(block_tpl.render(Context({})), 'Elle est de 100%')

    def test_translates_with_string_that_look_like_fmt_spec_with_trans(self):
        # tests "%s"
        expected = ('On dirait un spec str fmt %s mais ne devrait pas être interprété comme plus disponible')
        trans_tpl = Template(
            '{% load i18n %}{% trans "Looks like a str fmt spec %s but '
            'should not be interpreted as such" %}'
        )
        self.assertEqual(trans_tpl.render(Context({})), expected)
        block_tpl = Template(
            '{% load i18n %}{% blocktrans %}Looks like a str fmt spec %s but '
            'should not be interpreted as such{% endblocktrans %}'
        )
        self.assertEqual(block_tpl.render(Context({})), expected)

        # tests "% o"
        expected = ('On dirait un spec str fmt % o mais ne devrait pas être interprété comme plus disponible')
        trans_tpl = Template(
            '{% load i18n %}{% trans "Looks like a str fmt spec % o but should not be '
            'interpreted as such" %}'
        )
        self.assertEqual(trans_tpl.render(Context({})), expected)
        block_tpl = Template(
            '{% load i18n %}{% blocktrans %}Looks like a str fmt spec % o but should not be '
            'interpreted as such{% endblocktrans %}'
        )
        self.assertEqual(block_tpl.render(Context({})), expected)

    def test_translates_multiple_percent_signs(self):
        expected = ('1 % signe pour cent, signes %% 2 pour cent, trois signes de pourcentage %%%')

        trans_tpl = Template(
            '{% load i18n %}{% trans "1 percent sign %, 2 percent signs %%, '
            '3 percent signs %%%" %}'
        )
        self.assertEqual(trans_tpl.render(Context({})), expected)
        block_tpl = Template(
            '{% load i18n %}{% blocktrans %}1 percent sign %, 2 percent signs '
            '%%, 3 percent signs %%%{% endblocktrans %}'
        )
        self.assertEqual(block_tpl.render(Context({})), expected)

        block_tpl = Template(
            '{% load i18n %}{% blocktrans %}{{name}} says: 1 percent sign %, '
            '2 percent signs %%{% endblocktrans %}'
        )
        self.assertEqual(
            block_tpl.render(Context({"name": "Django"})),
            'Django dit: 1 pour cent signe %, deux signes de pourcentage %%'
        )
