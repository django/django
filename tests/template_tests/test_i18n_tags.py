# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.conf import settings
from django.template import Context, Template
from django.test import SimpleTestCase
from django.utils import translation
from django.utils._os import upath
from django.utils.translation import activate, get_language

here = os.path.dirname(os.path.dirname(os.path.abspath(upath(__file__))))
extended_locale_paths = settings.LOCALE_PATHS + [
    os.path.join(here, 'i18n', 'other', 'locale'),
]


class MultipleLocaleActivationTests(SimpleTestCase):
    """
    Tests for template rendering behavior when multiple locales are activated
    during the lifetime of the same process.
    """
    def setUp(self):
        super(MultipleLocaleActivationTests, self).setUp()
        self._old_language = get_language()

    def tearDown(self):
        super(MultipleLocaleActivationTests, self).tearDown()
        activate(self._old_language)

    def test_single_locale_activation(self):
        """
        Simple baseline behavior with one locale for all the supported i18n constructs.
        """
        with translation.override('fr'):
            self.assertEqual(Template("{{ _('Yes') }}").render(Context({})), 'Oui')

    # Literal marked up with _() in a filter expression

    def test_multiple_locale_filter(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{{ 0|yesno:_('yes,no,maybe') }}")
        with translation.override(self._old_language), translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'nee')

    def test_multiple_locale_filter_deactivate(self):
        with translation.override('de', deactivate=True):
            t = Template("{% load i18n %}{{ 0|yesno:_('yes,no,maybe') }}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'nee')

    def test_multiple_locale_filter_direct_switch(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{{ 0|yesno:_('yes,no,maybe') }}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'nee')

    # Literal marked up with _()

    def test_multiple_locale(self):
        with translation.override('de'):
            t = Template("{{ _('No') }}")
        with translation.override(self._old_language), translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_deactivate(self):
        with translation.override('de', deactivate=True):
            t = Template("{{ _('No') }}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_direct_switch(self):
        with translation.override('de'):
            t = Template("{{ _('No') }}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    # Literal marked up with _(), loading the i18n template tag library

    def test_multiple_locale_loadi18n(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{{ _('No') }}")
        with translation.override(self._old_language), translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_loadi18n_deactivate(self):
        with translation.override('de', deactivate=True):
            t = Template("{% load i18n %}{{ _('No') }}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')

    def test_multiple_locale_loadi18n_direct_switch(self):
        with translation.override('de'):
            t = Template("{% load i18n %}{{ _('No') }}")
        with translation.override('nl'):
            self.assertEqual(t.render(Context({})), 'Nee')
