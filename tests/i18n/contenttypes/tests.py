import os

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.utils import translation
from django.utils._os import upath


@override_settings(
    USE_I18N=True,
    LOCALE_PATHS=[
        os.path.join(os.path.dirname(upath(__file__)), 'locale'),
    ],
    LANGUAGE_CODE='en',
    LANGUAGES=[
        ('en', 'English'),
        ('fr', 'French'),
    ],
)
class ContentTypeTests(TestCase):
    def test_verbose_name(self):
        company_type = ContentType.objects.get(app_label='i18n', model='company')
        with translation.override('en'):
            self.assertEqual(str(company_type), 'Company')
        with translation.override('fr'):
            self.assertEqual(str(company_type), 'Société')
