# coding: utf-8
from __future__ import unicode_literals

import os

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation
from django.utils.py3 import text_type


@override_settings(
    USE_I18N=True,
    LOCALE_PATHS=(
        os.path.join(os.path.dirname(__file__), 'locale'),
    ),
    LANGUAGE_CODE='en',
    LANGUAGES=(
        ('en', 'English'),
        ('fr', 'French'),
    ),
)
class ContentTypeTests(TestCase):
    def test_verbose_name(self):
        company_type = ContentType.objects.get(app_label='i18n', model='company')
        with translation.override('en'):
            self.assertEqual(text_type(company_type), 'Company')
        with translation.override('fr'):
            self.assertEqual(text_type(company_type), 'Société')

    def test_field_override(self):
        company_type = ContentType.objects.get(app_label='i18n', model='company')
        company_type.name = 'Other'
        self.assertEqual(text_type(company_type), 'Other')
