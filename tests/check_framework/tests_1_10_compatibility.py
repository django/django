from django.core.checks.compatibility.django_1_10 import \
    check_duplicate_middleware_settings
from django.test import SimpleTestCase
from django.test.utils import override_settings


class CheckDuplicateMiddlwareSettingsTest(SimpleTestCase):

    @override_settings(MIDDLEWARE=[], MIDDLEWARE_CLASSES=['django.middleware.common.CommonMiddleware'])
    def test_duplicate_setting(self):
        result = check_duplicate_middleware_settings(None)
        self.assertEqual(result[0].id, '1_10.W001')

    @override_settings(MIDDLEWARE=None)
    def test_middleware_not_defined(self):
        result = check_duplicate_middleware_settings(None)
        self.assertEqual(len(result), 0)
