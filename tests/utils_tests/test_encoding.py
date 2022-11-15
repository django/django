import datetime
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote_plus

from django.test import SimpleTestCase
from django.utils.encoding import (
    DjangoUnicodeDecodeError,
    escape_uri_path,
    filepath_to_uri,
    force_bytes,
    force_str,
    get_system_encoding,
    iri_to_uri,
    punycode,
    repercent_broken_unicode,
    smart_bytes,
    smart_str,
    uri_to_iri,
)
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy

try:
    # try importing idna package for IDNA 2008 compliance
    import idna
except ImportError:
    idna = None


class TestEncodingUtils(SimpleTestCase):
    def test_force_str_exception(self):
        """
        Broken __str__ actually raises an error.
        """

        class MyString:
            def __str__(self):
                return b"\xc3\xb6\xc3\xa4\xc3\xbc"

        # str(s) raises a TypeError if the result is not a text type.
        with self.assertRaises(TypeError):
            force_str(MyString())

    def test_force_str_lazy(self):
        s = SimpleLazyObject(lambda: "x")
        self.assertIs(type(force_str(s)), str)

    def test_force_str_DjangoUnicodeDecodeError(self):
        msg = (
            "'utf-8' codec can't decode byte 0xff in position 0: invalid "
            "start byte. You passed in b'\\xff' (<class 'bytes'>)"
        )
        with self.assertRaisesMessage(DjangoUnicodeDecodeError, msg):
            force_str(b"\xff")

    def test_force_bytes_exception(self):
        """
        force_bytes knows how to convert to bytes an exception
        containing non-ASCII characters in its args.
        """
        error_msg = "This is an exception, voilà"
        exc = ValueError(error_msg)
        self.assertEqual(force_bytes(exc), error_msg.encode())
        self.assertEqual(
            force_bytes(exc, encoding="ascii", errors="ignore"),
            b"This is an exception, voil",
        )

    def test_force_bytes_strings_only(self):
        today = datetime.date.today()
        self.assertEqual(force_bytes(today, strings_only=True), today)

    def test_force_bytes_encoding(self):
        error_msg = "This is an exception, voilà".encode()
        result = force_bytes(error_msg, encoding="ascii", errors="ignore")
        self.assertEqual(result, b"This is an exception, voil")

    def test_force_bytes_memory_view(self):
        data = b"abc"
        result = force_bytes(memoryview(data))
        # Type check is needed because memoryview(bytes) == bytes.
        self.assertIs(type(result), bytes)
        self.assertEqual(result, data)

    def test_smart_bytes(self):
        class Test:
            def __str__(self):
                return "ŠĐĆŽćžšđ"

        lazy_func = gettext_lazy("x")
        self.assertIs(smart_bytes(lazy_func), lazy_func)
        self.assertEqual(
            smart_bytes(Test()),
            b"\xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91",
        )
        self.assertEqual(smart_bytes(1), b"1")
        self.assertEqual(smart_bytes("foo"), b"foo")

    def test_smart_str(self):
        class Test:
            def __str__(self):
                return "ŠĐĆŽćžšđ"

        lazy_func = gettext_lazy("x")
        self.assertIs(smart_str(lazy_func), lazy_func)
        self.assertEqual(
            smart_str(Test()), "\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111"
        )
        self.assertEqual(smart_str(1), "1")
        self.assertEqual(smart_str("foo"), "foo")

    def test_get_default_encoding(self):
        with mock.patch("locale.getlocale", side_effect=Exception):
            self.assertEqual(get_system_encoding(), "ascii")

    def test_repercent_broken_unicode_recursion_error(self):
        # Prepare a string long enough to force a recursion error if the tested
        # function uses recursion.
        data = b"\xfc" * sys.getrecursionlimit()
        try:
            self.assertEqual(
                repercent_broken_unicode(data), b"%FC" * sys.getrecursionlimit()
            )
        except RecursionError:
            self.fail("Unexpected RecursionError raised.")


class TestRFC3987IEncodingUtils(unittest.TestCase):
    def test_filepath_to_uri(self):
        self.assertIsNone(filepath_to_uri(None))
        self.assertEqual(
            filepath_to_uri("upload\\чубака.mp4"),
            "upload/%D1%87%D1%83%D0%B1%D0%B0%D0%BA%D0%B0.mp4",
        )
        self.assertEqual(filepath_to_uri(Path("upload/test.png")), "upload/test.png")
        self.assertEqual(filepath_to_uri(Path("upload\\test.png")), "upload/test.png")

    def test_iri_to_uri(self):
        cases = [
            # Valid UTF-8 sequences are encoded.
            ("red%09rosé#red", "red%09ros%C3%A9#red"),
            ("/blog/for/Jürgen Münster/", "/blog/for/J%C3%BCrgen%20M%C3%BCnster/"),
            (
                "locations/%s" % quote_plus("Paris & Orléans"),
                "locations/Paris+%26+Orl%C3%A9ans",
            ),
            # Reserved chars remain unescaped.
            ("%&", "%&"),
            ("red&♥ros%#red", "red&%E2%99%A5ros%#red"),
            (gettext_lazy("red&♥ros%#red"), "red&%E2%99%A5ros%#red"),
        ]

        for iri, uri in cases:
            with self.subTest(iri):
                self.assertEqual(iri_to_uri(iri), uri)

                # Test idempotency.
                self.assertEqual(iri_to_uri(iri_to_uri(iri)), uri)

    def test_uri_to_iri(self):
        cases = [
            (None, None),
            # Valid UTF-8 sequences are decoded.
            ("/%e2%89%Ab%E2%99%a5%E2%89%aB/", "/≫♥≫/"),
            ("/%E2%99%A5%E2%99%A5/?utf8=%E2%9C%93", "/♥♥/?utf8=✓"),
            ("/%41%5a%6B/", "/AZk/"),
            # Reserved and non-URL valid ASCII chars are not decoded.
            ("/%25%20%02%41%7b/", "/%25%20%02A%7b/"),
            # Broken UTF-8 sequences remain escaped.
            ("/%AAd%AAj%AAa%AAn%AAg%AAo%AA/", "/%AAd%AAj%AAa%AAn%AAg%AAo%AA/"),
            ("/%E2%99%A5%E2%E2%99%A5/", "/♥%E2♥/"),
            ("/%E2%99%A5%E2%99%E2%99%A5/", "/♥%E2%99♥/"),
            ("/%E2%E2%99%A5%E2%99%A5%99/", "/%E2♥♥%99/"),
            (
                "/%E2%99%A5%E2%99%A5/?utf8=%9C%93%E2%9C%93%9C%93",
                "/♥♥/?utf8=%9C%93✓%9C%93",
            ),
        ]

        for uri, iri in cases:
            with self.subTest(uri):
                self.assertEqual(uri_to_iri(uri), iri)

                # Test idempotency.
                self.assertEqual(uri_to_iri(uri_to_iri(uri)), iri)

    def test_complementarity(self):
        cases = [
            (
                "/blog/for/J%C3%BCrgen%20M%C3%BCnster/",
                "/blog/for/J\xfcrgen%20M\xfcnster/",
            ),
            ("%&", "%&"),
            ("red&%E2%99%A5ros%#red", "red&♥ros%#red"),
            ("/%E2%99%A5%E2%99%A5/", "/♥♥/"),
            ("/%E2%99%A5%E2%99%A5/?utf8=%E2%9C%93", "/♥♥/?utf8=✓"),
            ("/%25%20%02%7b/", "/%25%20%02%7b/"),
            ("/%AAd%AAj%AAa%AAn%AAg%AAo%AA/", "/%AAd%AAj%AAa%AAn%AAg%AAo%AA/"),
            ("/%E2%99%A5%E2%E2%99%A5/", "/♥%E2♥/"),
            ("/%E2%99%A5%E2%99%E2%99%A5/", "/♥%E2%99♥/"),
            ("/%E2%E2%99%A5%E2%99%A5%99/", "/%E2♥♥%99/"),
            (
                "/%E2%99%A5%E2%99%A5/?utf8=%9C%93%E2%9C%93%9C%93",
                "/♥♥/?utf8=%9C%93✓%9C%93",
            ),
        ]

        for uri, iri in cases:
            with self.subTest(uri):
                self.assertEqual(iri_to_uri(uri_to_iri(uri)), uri)
                self.assertEqual(uri_to_iri(iri_to_uri(iri)), iri)

    def test_escape_uri_path(self):
        cases = [
            (
                "/;some/=awful/?path/:with/@lots/&of/+awful/chars",
                "/%3Bsome/%3Dawful/%3Fpath/:with/@lots/&of/+awful/chars",
            ),
            ("/foo#bar", "/foo%23bar"),
            ("/foo?bar", "/foo%3Fbar"),
        ]
        for uri, expected in cases:
            with self.subTest(uri):
                self.assertEqual(escape_uri_path(uri), expected)


class TestPunycodeEncoding(unittest.TestCase):
    def test_valid_punycode(self):
        self.assertIsNone(punycode(None))
        self.assertEqual(punycode(""), "")

        cases = [
            ("xn----f38am99bqvcd5liy1cxsg.test", "xn----f38am99bqvcd5liy1cxsg.test"),
            ("test.xn--rhqv96g", "test.xn--rhqv96g"),
            ("test.شبك", "test.xn--ngbx0c"),
            ("普遍接受-测试.top", "xn----f38am99bqvcd5liy1cxsg.top"),
            ("मेल.डाटामेल.भारत", "xn--r2bi6d.xn--c2bd4bq1db8d.xn--h2brj9c"),
            ("fußball.de", "xn--fuball-cta.de" if idna else "fussball.de"),
        ]

        for ulabel, alabel in cases:
            with self.subTest(ulabel):
                self.assertEqual(punycode(ulabel), alabel)

    def test_invalid_punycode(self):
        cases = [".test.top"]
        if idna:
            cases += ["in--valid", "\\u0557w.test"]

        for label in cases:
            with self.subTest(label):
                with self.assertRaises(UnicodeError):
                    punycode(label)
