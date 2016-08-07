# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.forms import URLField, ValidationError
from django.test import SimpleTestCase

from . import FormFieldAssertionsMixin


class URLFieldTest(FormFieldAssertionsMixin, SimpleTestCase):

    def test_urlfield_1(self):
        f = URLField()
        self.assertWidgetRendersTo(f, '<input type="url" name="f" id="id_f" required />')
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean('')
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertEqual('http://localhost', f.clean('http://localhost'))
        self.assertEqual('http://example.com', f.clean('http://example.com'))
        self.assertEqual('http://example.com.', f.clean('http://example.com.'))
        self.assertEqual('http://www.example.com', f.clean('http://www.example.com'))
        self.assertEqual('http://www.example.com:8000/test', f.clean('http://www.example.com:8000/test'))
        self.assertEqual('http://valid-with-hyphens.com', f.clean('valid-with-hyphens.com'))
        self.assertEqual('http://subdomain.domain.com', f.clean('subdomain.domain.com'))
        self.assertEqual('http://200.8.9.10', f.clean('http://200.8.9.10'))
        self.assertEqual('http://200.8.9.10:8000/test', f.clean('http://200.8.9.10:8000/test'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('foo')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://example')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://example.')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('com.')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('.')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://.com')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://invalid-.com')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://-invalid.com')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://inv-.alid-.com')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://inv-.-alid.com')
        self.assertEqual('http://valid-----hyphens.com', f.clean('http://valid-----hyphens.com'))
        self.assertEqual(
            'http://some.idn.xyz\xe4\xf6\xfc\xdfabc.domain.com:123/blah',
            f.clean('http://some.idn.xyzäöüßabc.domain.com:123/blah')
        )
        self.assertEqual(
            'http://www.example.com/s/http://code.djangoproject.com/ticket/13804',
            f.clean('www.example.com/s/http://code.djangoproject.com/ticket/13804')
        )
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('[a')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://[a')

    def test_url_regex_ticket11198(self):
        f = URLField()
        # hangs "forever" if catastrophic backtracking in ticket:#11198 not fixed
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://%s' % ("X" * 200,))

        # a second test, to make sure the problem is really addressed, even on
        # domains that don't fail the domain label length check in the regex
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://%s' % ("X" * 60,))

    def test_urlfield_2(self):
        f = URLField(required=False)
        self.assertEqual('', f.clean(''))
        self.assertEqual('', f.clean(None))
        self.assertEqual('http://example.com', f.clean('http://example.com'))
        self.assertEqual('http://www.example.com', f.clean('http://www.example.com'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('foo')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://example')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://example.')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean('http://.com')

    def test_urlfield_5(self):
        f = URLField(min_length=15, max_length=20)
        self.assertWidgetRendersTo(f, '<input id="id_f" type="url" name="f" maxlength="20" minlength="15" required />')
        with self.assertRaisesMessage(ValidationError, "'Ensure this value has at least 15 characters (it has 12).'"):
            f.clean('http://f.com')
        self.assertEqual('http://example.com', f.clean('http://example.com'))
        with self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 20 characters (it has 37).'"):
            f.clean('http://abcdefghijklmnopqrstuvwxyz.com')

    def test_urlfield_6(self):
        f = URLField(required=False)
        self.assertEqual('http://example.com', f.clean('example.com'))
        self.assertEqual('', f.clean(''))
        self.assertEqual('https://example.com', f.clean('https://example.com'))

    def test_urlfield_7(self):
        f = URLField()
        self.assertEqual('http://example.com', f.clean('http://example.com'))
        self.assertEqual('http://example.com/test', f.clean('http://example.com/test'))
        self.assertEqual(
            'http://example.com?some_param=some_value',
            f.clean('http://example.com?some_param=some_value')
        )

    def test_urlfield_9(self):
        f = URLField()
        urls = (
            'http://עברית.idn.icann.org/',
            'http://sãopaulo.com/',
            'http://sãopaulo.com.br/',
            'http://пример.испытание/',
            'http://مثال.إختبار/',
            'http://例子.测试/',
            'http://例子.測試/',
            'http://उदाहरण.परीक्षा/',
            'http://例え.テスト/',
            'http://مثال.آزمایشی/',
            'http://실례.테스트/',
            'http://العربية.idn.icann.org/',
        )
        for url in urls:
            # Valid IDN
            self.assertEqual(url, f.clean(url))

    def test_urlfield_10(self):
        """URLField correctly validates IPv6 (#18779)."""
        f = URLField()
        urls = (
            'http://[12:34::3a53]/',
            'http://[a34:9238::]:8080/',
        )
        for url in urls:
            self.assertEqual(url, f.clean(url))

    def test_urlfield_not_string(self):
        f = URLField(required=False)
        with self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'"):
            f.clean(23)

    def test_urlfield_normalization(self):
        f = URLField()
        self.assertEqual(f.clean('http://example.com/     '), 'http://example.com/')

    def test_urlfield_strip_on_none_value(self):
        f = URLField(required=False, empty_value=None)
        self.assertIsNone(f.clean(None))

    def test_urlfield_unable_to_set_strip_kwarg(self):
        msg = "__init__() got multiple values for keyword argument 'strip'"
        with self.assertRaisesMessage(TypeError, msg):
            URLField(strip=False)
