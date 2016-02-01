from django.conf import settings
from django.core.checks.urls import check_url_config
from django.test import SimpleTestCase
from django.test.utils import override_settings


class CheckUrlsTest(SimpleTestCase):
    @override_settings(ROOT_URLCONF='check_framework.urls.no_warnings')
    def test_no_warnings(self):
        result = check_url_config(None)
        self.assertEqual(result, [])

    @override_settings(ROOT_URLCONF='check_framework.urls.include_with_dollar')
    def test_include_with_dollar(self):
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, 'urls.W001')
        expected_msg = "Your URL pattern '^include-with-dollar$' uses include with a regex ending with a '$'."
        self.assertIn(expected_msg, warning.msg)

    @override_settings(ROOT_URLCONF='check_framework.urls.beginning_with_slash')
    def test_beginning_with_slash(self):
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, 'urls.W002')
        expected_msg = "Your URL pattern '/starting-with-slash/$' has a regex beginning with a '/'"
        self.assertIn(expected_msg, warning.msg)

    @override_settings(ROOT_URLCONF='check_framework.urls.name_with_colon')
    def test_name_with_colon(self):
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, 'urls.W003')
        expected_msg = "Your URL pattern '^$' [name='name_with:colon'] has a name including a ':'."
        self.assertIn(expected_msg, warning.msg)

    @override_settings(ROOT_URLCONF=None)
    def test_no_root_urlconf_in_settings(self):
        delattr(settings, 'ROOT_URLCONF')
        result = check_url_config(None)
        self.assertEqual(result, [])
