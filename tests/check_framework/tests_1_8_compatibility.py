from django.core.checks.compatibility.django_1_8_0 import \
    check_duplicate_template_settings
from django.test import SimpleTestCase
from django.test.utils import override_settings


class CheckDuplicateTemplateSettingsTest(SimpleTestCase):

    def test_not_raised_if_no_templates_setting(self):
        self.assertEqual(check_duplicate_template_settings(None), [])

    @override_settings(
        TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates'}],
        TEMPLATE_DIRS=['/path/to/dirs'],
    )
    def test_duplicate_setting(self):
        result = check_duplicate_template_settings(None)
        self.assertEqual(result[0].id, '1_8.W001')

    @override_settings(
        TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates'}],
        TEMPLATE_DIRS=['/path/to/dirs'],
        TEMPLATE_DEBUG=True,
    )
    def test_multiple_duplicate_settings(self):
        result = check_duplicate_template_settings(None)
        self.assertEqual(len(result), 1)
        self.assertIn('TEMPLATE_DIRS', result[0].msg)
        self.assertIn('TEMPLATE_DEBUG', result[0].msg)
