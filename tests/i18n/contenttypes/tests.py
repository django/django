from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.utils import translation


@override_settings(
    USE_I18N=True,
    LOCALE_PATHS=[
        Path(__file__).parent / "locale",
    ],
    LANGUAGE_CODE="en",
    LANGUAGES=[
        ("en", "English"),
        ("fr", "French"),
    ],
)
class ContentTypeTests(TestCase):
    def test_verbose_name(self):
        company_type = ContentType.objects.get(app_label="i18n", model="company")
        with translation.override("en"):
            self.assertEqual(str(company_type), "i18n | Company")
        with translation.override("fr"):
            self.assertEqual(str(company_type), "i18n | Société")
