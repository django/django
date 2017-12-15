from django.conf import settings
from django.core.checks.messages import Warning
from django.core.checks.urls import (
    E006, check_url_config, check_url_namespaces_unique, check_url_settings,
    get_warning_for_invalid_pattern,
)
from django.test import SimpleTestCase
from django.test.utils import override_settings


class CheckUrlConfigTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF='check_framework.urls.no_warnings')
    def test_no_warnings(self):
        result = check_url_config(None)
        self.assertEqual(result, [])

    @override_settings(ROOT_URLCONF='check_framework.urls.no_warnings_i18n')
    def test_no_warnings_i18n(self):
        self.assertEqual(check_url_config(None), [])

    @override_settings(ROOT_URLCONF='check_framework.urls.warning_in_include')
    def test_check_resolver_recursive(self):
        # The resolver is checked recursively (examining url()s in include()).
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, 'urls.W001')

    @override_settings(ROOT_URLCONF='check_framework.urls.include_with_dollar')
    def test_include_with_dollar(self):
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, 'urls.W001')
        self.assertEqual(warning.msg, (
            "Your URL pattern '^include-with-dollar$' uses include with a "
            "route ending with a '$'. Remove the dollar from the route to "
            "avoid problems including URLs."
        ))

    @override_settings(ROOT_URLCONF='check_framework.urls.contains_tuple')
    def test_contains_tuple_not_url_instance(self):
        result = check_url_config(None)
        warning = result[0]
        self.assertEqual(warning.id, 'urls.E004')
        self.assertRegex(warning.msg, (
            r"^Your URL pattern \('\^tuple/\$', <function <lambda> at 0x(\w+)>\) is "
            r"invalid. Ensure that urlpatterns is a list of path\(\) and/or re_path\(\) "
            r"instances\.$"
        ))

    @override_settings(ROOT_URLCONF='check_framework.urls.include_contains_tuple')
    def test_contains_included_tuple(self):
        result = check_url_config(None)
        warning = result[0]
        self.assertEqual(warning.id, 'urls.E004')
        self.assertRegex(warning.msg, (
            r"^Your URL pattern \('\^tuple/\$', <function <lambda> at 0x(\w+)>\) is "
            r"invalid. Ensure that urlpatterns is a list of path\(\) and/or re_path\(\) "
            r"instances\.$"
        ))

    @override_settings(ROOT_URLCONF='check_framework.urls.beginning_with_slash')
    def test_beginning_with_slash(self):
        msg = (
            "Your URL pattern '%s' has a route beginning with a '/'. Remove "
            "this slash as it is unnecessary. If this pattern is targeted in "
            "an include(), ensure the include() pattern has a trailing '/'."
        )
        warning1, warning2 = check_url_config(None)
        self.assertEqual(warning1.id, 'urls.W002')
        self.assertEqual(warning1.msg, msg % '/path-starting-with-slash/')
        self.assertEqual(warning2.id, 'urls.W002')
        self.assertEqual(warning2.msg, msg % '/url-starting-with-slash/$')

    @override_settings(
        ROOT_URLCONF='check_framework.urls.beginning_with_slash',
        APPEND_SLASH=False,
    )
    def test_beginning_with_slash_append_slash(self):
        # It can be useful to start a URL pattern with a slash when
        # APPEND_SLASH=False (#27238).
        result = check_url_config(None)
        self.assertEqual(result, [])

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

    def test_get_warning_for_invalid_pattern_string(self):
        warning = get_warning_for_invalid_pattern('')[0]
        self.assertEqual(
            warning.hint,
            "Try removing the string ''. The list of urlpatterns should "
            "not have a prefix string as the first element.",
        )

    def test_get_warning_for_invalid_pattern_tuple(self):
        warning = get_warning_for_invalid_pattern((r'^$', lambda x: x))[0]
        self.assertEqual(warning.hint, "Try using path() instead of a tuple.")

    def test_get_warning_for_invalid_pattern_other(self):
        warning = get_warning_for_invalid_pattern(object())[0]
        self.assertIsNone(warning.hint)

    @override_settings(ROOT_URLCONF='check_framework.urls.non_unique_namespaces')
    def test_check_non_unique_namespaces(self):
        result = check_url_namespaces_unique(None)
        self.assertEqual(len(result), 2)
        non_unique_namespaces = ['app-ns1', 'app-1']
        warning_messages = [
            "URL namespace '{}' isn't unique. You may not be able to reverse "
            "all URLs in this namespace".format(namespace)
            for namespace in non_unique_namespaces
        ]
        for warning in result:
            self.assertIsInstance(warning, Warning)
            self.assertEqual('urls.W005', warning.id)
            self.assertIn(warning.msg, warning_messages)

    @override_settings(ROOT_URLCONF='check_framework.urls.unique_namespaces')
    def test_check_unique_namespaces(self):
        result = check_url_namespaces_unique(None)
        self.assertEqual(result, [])


class UpdatedToPathTests(SimpleTestCase):

    @override_settings(ROOT_URLCONF='check_framework.urls.path_compatibility.contains_re_named_group')
    def test_contains_re_named_group(self):
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, '2_0.W001')
        expected_msg = "Your URL pattern '(?P<named-group>\\d+)' has a route"
        self.assertIn(expected_msg, warning.msg)

    @override_settings(ROOT_URLCONF='check_framework.urls.path_compatibility.beginning_with_caret')
    def test_beginning_with_caret(self):
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, '2_0.W001')
        expected_msg = "Your URL pattern '^beginning-with-caret' has a route"
        self.assertIn(expected_msg, warning.msg)

    @override_settings(ROOT_URLCONF='check_framework.urls.path_compatibility.ending_with_dollar')
    def test_ending_with_dollar(self):
        result = check_url_config(None)
        self.assertEqual(len(result), 1)
        warning = result[0]
        self.assertEqual(warning.id, '2_0.W001')
        expected_msg = "Your URL pattern 'ending-with-dollar$' has a route"
        self.assertIn(expected_msg, warning.msg)


class CheckURLSettingsTests(SimpleTestCase):

    @override_settings(STATIC_URL='a/', MEDIA_URL='b/')
    def test_slash_no_errors(self):
        self.assertEqual(check_url_settings(None), [])

    @override_settings(STATIC_URL='', MEDIA_URL='')
    def test_empty_string_no_errors(self):
        self.assertEqual(check_url_settings(None), [])

    @override_settings(STATIC_URL='noslash')
    def test_static_url_no_slash(self):
        self.assertEqual(check_url_settings(None), [E006('STATIC_URL')])

    @override_settings(STATIC_URL='slashes//')
    def test_static_url_double_slash_allowed(self):
        # The check allows for a double slash, presuming the user knows what
        # they are doing.
        self.assertEqual(check_url_settings(None), [])

    @override_settings(MEDIA_URL='noslash')
    def test_media_url_no_slash(self):
        self.assertEqual(check_url_settings(None), [E006('MEDIA_URL')])
