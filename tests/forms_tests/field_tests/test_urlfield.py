import sys
from types import ModuleType

from django.conf import FORMS_URLFIELD_ASSUME_HTTPS_DEPRECATED_MSG, Settings, settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.forms import URLField
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango60Warning

from . import FormFieldAssertionsMixin


@ignore_warnings(category=RemovedInDjango60Warning)
class URLFieldTest(FormFieldAssertionsMixin, SimpleTestCase):
    def test_urlfield_widget(self):
        f = URLField()
        self.assertWidgetRendersTo(f, '<input type="url" name="f" id="id_f" required>')

    def test_urlfield_widget_max_min_length(self):
        f = URLField(min_length=15, max_length=20)
        self.assertEqual("http://example.com", f.clean("http://example.com"))
        self.assertWidgetRendersTo(
            f,
            '<input id="id_f" type="url" name="f" maxlength="20" '
            'minlength="15" required>',
        )
        msg = "'Ensure this value has at least 15 characters (it has 12).'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("http://f.com")
        msg = "'Ensure this value has at most 20 characters (it has 37).'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("http://abcdefghijklmnopqrstuvwxyz.com")

    def test_urlfield_clean(self):
        # RemovedInDjango60Warning: When the deprecation ends, remove the
        # assume_scheme argument.
        f = URLField(required=False, assume_scheme="https")
        tests = [
            ("http://localhost", "http://localhost"),
            ("http://example.com", "http://example.com"),
            ("http://example.com/test", "http://example.com/test"),
            ("http://example.com.", "http://example.com."),
            ("http://www.example.com", "http://www.example.com"),
            ("http://www.example.com:8000/test", "http://www.example.com:8000/test"),
            (
                "http://example.com?some_param=some_value",
                "http://example.com?some_param=some_value",
            ),
            ("valid-with-hyphens.com", "https://valid-with-hyphens.com"),
            ("subdomain.domain.com", "https://subdomain.domain.com"),
            ("http://200.8.9.10", "http://200.8.9.10"),
            ("http://200.8.9.10:8000/test", "http://200.8.9.10:8000/test"),
            ("http://valid-----hyphens.com", "http://valid-----hyphens.com"),
            (
                "http://some.idn.xyzäöüßabc.domain.com:123/blah",
                "http://some.idn.xyz\xe4\xf6\xfc\xdfabc.domain.com:123/blah",
            ),
            (
                "www.example.com/s/http://code.djangoproject.com/ticket/13804",
                "https://www.example.com/s/http://code.djangoproject.com/ticket/13804",
            ),
            # Normalization.
            ("http://example.com/     ", "http://example.com/"),
            # Valid IDN.
            ("http://עברית.idn.icann.org/", "http://עברית.idn.icann.org/"),
            ("http://sãopaulo.com/", "http://sãopaulo.com/"),
            ("http://sãopaulo.com.br/", "http://sãopaulo.com.br/"),
            ("http://пример.испытание/", "http://пример.испытание/"),
            ("http://مثال.إختبار/", "http://مثال.إختبار/"),
            ("http://例子.测试/", "http://例子.测试/"),
            ("http://例子.測試/", "http://例子.測試/"),
            (
                "http://उदाहरण.परीक्षा/",
                "http://उदाहरण.परीक्षा/",
            ),
            ("http://例え.テスト/", "http://例え.テスト/"),
            ("http://مثال.آزمایشی/", "http://مثال.آزمایشی/"),
            ("http://실례.테스트/", "http://실례.테스트/"),
            ("http://العربية.idn.icann.org/", "http://العربية.idn.icann.org/"),
            # IPv6.
            ("http://[12:34::3a53]/", "http://[12:34::3a53]/"),
            ("http://[a34:9238::]:8080/", "http://[a34:9238::]:8080/"),
            # IPv6 without scheme.
            ("[12:34::3a53]/", "https://[12:34::3a53]/"),
            # IDN domain without scheme but with port.
            ("ñandú.es:8080/", "https://ñandú.es:8080/"),
            # Scheme-relative.
            ("//example.com", "https://example.com"),
            ("//example.com/path", "https://example.com/path"),
            # Whitespace stripped.
            ("\t\n//example.com  \n\t\n", "https://example.com"),
            ("\t\nhttp://example.com  \n\t\n", "http://example.com"),
        ]
        for url, expected in tests:
            with self.subTest(url=url):
                self.assertEqual(f.clean(url), expected)

    def test_urlfield_clean_invalid(self):
        f = URLField()
        tests = [
            "foo",
            "com.",
            ".",
            "http://",
            "http://example",
            "http://example.",
            "http://.com",
            "http://invalid-.com",
            "http://-invalid.com",
            "http://inv-.alid-.com",
            "http://inv-.-alid.com",
            "[a",
            "http://[a",
            # Non-string.
            23,
            # Hangs "forever" before fixing a catastrophic backtracking,
            # see #11198.
            "http://%s" % ("X" * 60,),
            # A second example, to make sure the problem is really addressed,
            # even on domains that don't fail the domain label length check in
            # the regex.
            "http://%s" % ("X" * 200,),
            # Scheme prepend yields a structurally invalid URL.
            "////]@N.AN",
            # Scheme prepend yields an empty hostname.
            "#@A.bO",
            # Known problematic unicode chars.
            "http://" + "¾" * 200,
            # Non-ASCII character before the first colon.
            "¾:example.com",
            # ASCII digit before the first colon.
            "1http://example.com",
            # Empty scheme.
            "://example.com",
            ":example.com",
        ]
        msg = "'Enter a valid URL.'"
        for value in tests:
            with self.subTest(value=value):
                with self.assertRaisesMessage(ValidationError, msg):
                    f.clean(value)

    def test_urlfield_clean_required(self):
        f = URLField()
        msg = "'This field is required.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(None)
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("")

    def test_urlfield_clean_not_required(self):
        f = URLField(required=False)
        self.assertEqual(f.clean(None), "")
        self.assertEqual(f.clean(""), "")

    def test_urlfield_strip_on_none_value(self):
        f = URLField(required=False, empty_value=None)
        self.assertIsNone(f.clean(""))
        self.assertIsNone(f.clean(None))

    def test_urlfield_unable_to_set_strip_kwarg(self):
        msg = "got multiple values for keyword argument 'strip'"
        with self.assertRaisesMessage(TypeError, msg):
            URLField(strip=False)

    def test_urlfield_assume_scheme(self):
        f = URLField()
        # RemovedInDjango60Warning: When the deprecation ends, replace with:
        # "https://example.com"
        self.assertEqual(f.clean("example.com"), "http://example.com")
        f = URLField(assume_scheme="http")
        self.assertEqual(f.clean("example.com"), "http://example.com")
        f = URLField(assume_scheme="https")
        self.assertEqual(f.clean("example.com"), "https://example.com")

    @override_settings(FORMS_URLFIELD_ASSUME_HTTPS=True)
    def test_urlfield_assume_scheme_when_colons(self):
        f = URLField()
        tests = [
            # Port number.
            ("http://example.com:8080/", "http://example.com:8080/"),
            ("https://example.com:443/path", "https://example.com:443/path"),
            # Userinfo with password.
            ("http://user:pass@example.com", "http://user:pass@example.com"),
            (
                "http://user:pass@example.com:8080/",
                "http://user:pass@example.com:8080/",
            ),
            # Colon in path segment.
            ("http://example.com/path:segment", "http://example.com/path:segment"),
            ("http://example.com/a:b/c:d", "http://example.com/a:b/c:d"),
            # Colon in query string.
            ("http://example.com/?key=val:ue", "http://example.com/?key=val:ue"),
            # Colon in fragment.
            ("http://example.com/#section:1", "http://example.com/#section:1"),
            # IPv6 -- multiple colons in host.
            ("http://[::1]/", "http://[::1]/"),
            ("http://[2001:db8::1]/", "http://[2001:db8::1]/"),
            ("http://[2001:db8::1]:8080/", "http://[2001:db8::1]:8080/"),
            # Colons across multiple components.
            (
                "http://user:pass@example.com:8080/path:x?q=a:b#id:1",
                "http://user:pass@example.com:8080/path:x?q=a:b#id:1",
            ),
            # FTP with port and userinfo.
            (
                "ftp://user:pass@ftp.example.com:21/file",
                "ftp://user:pass@ftp.example.com:21/file",
            ),
            (
                "ftps://user:pass@ftp.example.com:990/",
                "ftps://user:pass@ftp.example.com:990/",
            ),
            # Scheme-relative URLs, starts with "//".
            ("//example.com:8080/path", "https://example.com:8080/path"),
            ("//user:pass@example.com/", "https://user:pass@example.com/"),
        ]
        for value, expected in tests:
            with self.subTest(value=value):
                self.assertEqual(f.clean(value), expected)

    def test_custom_validator_longer_max_length(self):

        class CustomLongURLValidator(URLValidator):
            max_length = 4096

        class CustomURLField(URLField):
            default_validators = [CustomLongURLValidator()]

        field = CustomURLField()
        # A URL with 4096 chars is valid given the custom validator.
        prefix = "https://example.com/"
        url = prefix + "a" * (4096 - len(prefix))
        self.assertEqual(len(url), 4096)
        # No ValidationError is raised.
        field.clean(url)


class URLFieldAssumeSchemeDeprecationTest(FormFieldAssertionsMixin, SimpleTestCase):
    def test_urlfield_raises_warning(self):
        msg = (
            "The default scheme will be changed from 'http' to 'https' in Django 6.0. "
            "Pass the forms.URLField.assume_scheme argument to silence this warning, "
            "or set the FORMS_URLFIELD_ASSUME_HTTPS transitional setting to True to "
            "opt into using 'https' as the new default scheme."
        )
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg) as ctx:
            f = URLField()
            self.assertEqual(f.clean("example.com"), "http://example.com")
        self.assertEqual(ctx.filename, __file__)

    @ignore_warnings(category=RemovedInDjango60Warning)
    def test_urlfield_forms_urlfield_assume_https(self):
        with self.settings(FORMS_URLFIELD_ASSUME_HTTPS=True):
            f = URLField()
            self.assertEqual(f.clean("example.com"), "https://example.com")
            f = URLField(assume_scheme="http")
            self.assertEqual(f.clean("example.com"), "http://example.com")

    def test_override_forms_urlfield_assume_https_setting_warning(self):
        msg = FORMS_URLFIELD_ASSUME_HTTPS_DEPRECATED_MSG
        with self.assertRaisesMessage(RemovedInDjango60Warning, msg):
            # Changing FORMS_URLFIELD_ASSUME_HTTPS via self.settings() raises a
            # deprecation warning.
            with self.settings(FORMS_URLFIELD_ASSUME_HTTPS=True):
                pass

    def test_settings_init_forms_urlfield_assume_https_warning(self):
        settings_module = ModuleType("fake_settings_module")
        settings_module.FORMS_URLFIELD_ASSUME_HTTPS = True
        sys.modules["fake_settings_module"] = settings_module
        msg = FORMS_URLFIELD_ASSUME_HTTPS_DEPRECATED_MSG
        try:
            with self.assertRaisesMessage(RemovedInDjango60Warning, msg):
                Settings("fake_settings_module")
        finally:
            del sys.modules["fake_settings_module"]

    def test_access_forms_urlfield_assume_https(self):
        # Warning is not raised on access.
        self.assertEqual(settings.FORMS_URLFIELD_ASSUME_HTTPS, False)
