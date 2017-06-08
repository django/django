from django.contrib.csp.utils import build_policy
from django.test import TestCase
from django.test.utils import override_settings


def policy_eq(a, b, msg='%r != %r'):
    parts_a = sorted(a.split('; '))
    parts_b = sorted(b.split('; '))
    assert parts_a == parts_b, msg % (a, b)


class UtilsTests(TestCase):
    def test_empty_policy(self):
        policy = build_policy()
        self.assertEqual("default-src 'self'", policy)

    @override_settings(CSP_DEFAULT_SRC=['example.com', 'example2.com'])
    def test_default_src(self):
        policy = build_policy()
        self.assertEqual('default-src example.com example2.com', policy)

    @override_settings(CSP_SCRIPT_SRC=['example.com'])
    def test_script_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; script-src example.com", policy)

    @override_settings(CSP_OBJECT_SRC=['example.com'])
    def test_object_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; object-src example.com", policy)

    @override_settings(CSP_STYLE_SRC=['example.com'])
    def test_style_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; style-src example.com", policy)

    @override_settings(CSP_IMG_SRC=['example.com'])
    def test_img_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; img-src example.com", policy)

    @override_settings(CSP_MEDIA_SRC=['example.com'])
    def test_media_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; media-src example.com", policy)

    @override_settings(CSP_FRAME_SRC=['example.com'])
    def test_frame_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; frame-src example.com", policy)

    @override_settings(CSP_FONT_SRC=['example.com'])
    def test_font_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; font-src example.com", policy)

    @override_settings(CSP_CONNECT_SRC=['example.com'])
    def test_connect_src(self):
        policy = build_policy()
        policy_eq("default-src 'self'; connect-src example.com", policy)

    @override_settings(CSP_SANDBOX=['allow-scripts'])
    def test_sandbox(self):
        policy = build_policy()
        policy_eq("default-src 'self'; sandbox allow-scripts", policy)

    @override_settings(CSP_SANDBOX=[])
    def test_sandbox_empty(self):
        policy = build_policy()
        policy_eq("default-src 'self'; sandbox ", policy)

    @override_settings(CSP_REPORT_URI='/foo')
    def test_report_uri(self):
        policy = build_policy()
        policy_eq("default-src 'self'; report-uri /foo", policy)

    @override_settings(CSP_IMG_SRC=['example.com'])
    def test_update_img(self):
        policy = build_policy(update={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example.com example2.com",
                  policy)

    def test_update_missing_setting(self):
        """update should work even if the setting is not defined."""
        policy = build_policy(update={'img-src': 'example.com'})
        policy_eq("default-src 'self'; img-src example.com", policy)

    @override_settings(CSP_IMG_SRC=['example.com'])
    def test_replace_img(self):
        policy = build_policy(replace={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example2.com", policy)

    def test_replace_missing_setting(self):
        """replace should work even if the setting is not defined."""
        policy = build_policy(replace={'img-src': 'example.com'})
        policy_eq("default-src 'self'; img-src example.com", policy)

    def test_config(self):
        policy = build_policy(
            config={'default-src': ["'none'"], 'img-src': ["'self'"]})
        policy_eq("default-src 'none'; img-src 'self'", policy)

    @override_settings(CSP_IMG_SRC=('example.com',))
    def test_update_string(self):
        """
        GitHub issue #40 - given project settings as a tuple, and
        an update/replace with a string, concatenate correctly.
        """
        policy = build_policy(update={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example.com example2.com",
                  policy)

    @override_settings(CSP_IMG_SRC=('example.com',))
    def test_replace_string(self):
        """
        Demonstrate that GitHub issue #40 doesn't affect replacements
        """
        policy = build_policy(replace={'img-src': 'example2.com'})
        policy_eq("default-src 'self'; img-src example2.com",
                  policy)
