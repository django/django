from django.core.exceptions import ValidationError
from django.forms import URLField
from django.test import SimpleTestCase

from . import FormFieldAssertionsMixin


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
        f = URLField(required=False)
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
            ("valid-with-hyphens.com", "http://valid-with-hyphens.com"),
            ("subdomain.domain.com", "http://subdomain.domain.com"),
            ("http://200.8.9.10", "http://200.8.9.10"),
            ("http://200.8.9.10:8000/test", "http://200.8.9.10:8000/test"),
            ("http://valid-----hyphens.com", "http://valid-----hyphens.com"),
            (
                "http://some.idn.xyzäöüßabc.domain.com:123/blah",
                "http://some.idn.xyz\xe4\xf6\xfc\xdfabc.domain.com:123/blah",
            ),
            (
                "www.example.com/s/http://code.djangoproject.com/ticket/13804",
                "http://www.example.com/s/http://code.djangoproject.com/ticket/13804",
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
            # urlsplit() raises ValueError.
            "////]@N.AN",
            # Empty hostname.
            "#@A.bO",
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
        msg = "__init__() got multiple values for keyword argument 'strip'"
        with self.assertRaisesMessage(TypeError, msg):
            URLField(strip=False)
