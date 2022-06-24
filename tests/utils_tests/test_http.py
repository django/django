import platform
import unittest
from datetime import datetime, timezone
from unittest import mock

from django.test import SimpleTestCase
from django.utils.datastructures import MultiValueDict
from django.utils.http import (
    base36_to_int,
    escape_leading_slashes,
    http_date,
    int_to_base36,
    is_same_domain,
    parse_etags,
    parse_header_parameters,
    parse_http_date,
    quote_etag,
    url_has_allowed_host_and_scheme,
    urlencode,
    urlsafe_base64_decode,
    urlsafe_base64_encode,
)


class URLEncodeTests(SimpleTestCase):
    cannot_encode_none_msg = (
        "Cannot encode None for key 'a' in a query string. Did you mean to "
        "pass an empty string or omit the value?"
    )

    def test_tuples(self):
        self.assertEqual(urlencode((("a", 1), ("b", 2), ("c", 3))), "a=1&b=2&c=3")

    def test_dict(self):
        result = urlencode({"a": 1, "b": 2, "c": 3})
        # Dictionaries are treated as unordered.
        self.assertIn(
            result,
            [
                "a=1&b=2&c=3",
                "a=1&c=3&b=2",
                "b=2&a=1&c=3",
                "b=2&c=3&a=1",
                "c=3&a=1&b=2",
                "c=3&b=2&a=1",
            ],
        )

    def test_dict_containing_sequence_not_doseq(self):
        self.assertEqual(urlencode({"a": [1, 2]}, doseq=False), "a=%5B1%2C+2%5D")

    def test_dict_containing_tuple_not_doseq(self):
        self.assertEqual(urlencode({"a": (1, 2)}, doseq=False), "a=%281%2C+2%29")

    def test_custom_iterable_not_doseq(self):
        class IterableWithStr:
            def __str__(self):
                return "custom"

            def __iter__(self):
                yield from range(0, 3)

        self.assertEqual(urlencode({"a": IterableWithStr()}, doseq=False), "a=custom")

    def test_dict_containing_sequence_doseq(self):
        self.assertEqual(urlencode({"a": [1, 2]}, doseq=True), "a=1&a=2")

    def test_dict_containing_empty_sequence_doseq(self):
        self.assertEqual(urlencode({"a": []}, doseq=True), "")

    def test_multivaluedict(self):
        result = urlencode(
            MultiValueDict(
                {
                    "name": ["Adrian", "Simon"],
                    "position": ["Developer"],
                }
            ),
            doseq=True,
        )
        # MultiValueDicts are similarly unordered.
        self.assertIn(
            result,
            [
                "name=Adrian&name=Simon&position=Developer",
                "position=Developer&name=Adrian&name=Simon",
            ],
        )

    def test_dict_with_bytes_values(self):
        self.assertEqual(urlencode({"a": b"abc"}, doseq=True), "a=abc")

    def test_dict_with_sequence_of_bytes(self):
        self.assertEqual(
            urlencode({"a": [b"spam", b"eggs", b"bacon"]}, doseq=True),
            "a=spam&a=eggs&a=bacon",
        )

    def test_dict_with_bytearray(self):
        self.assertEqual(urlencode({"a": bytearray(range(2))}, doseq=True), "a=0&a=1")

    def test_generator(self):
        self.assertEqual(urlencode({"a": range(2)}, doseq=True), "a=0&a=1")
        self.assertEqual(urlencode({"a": range(2)}, doseq=False), "a=range%280%2C+2%29")

    def test_none(self):
        with self.assertRaisesMessage(TypeError, self.cannot_encode_none_msg):
            urlencode({"a": None})

    def test_none_in_sequence(self):
        with self.assertRaisesMessage(TypeError, self.cannot_encode_none_msg):
            urlencode({"a": [None]}, doseq=True)

    def test_none_in_generator(self):
        def gen():
            yield None

        with self.assertRaisesMessage(TypeError, self.cannot_encode_none_msg):
            urlencode({"a": gen()}, doseq=True)


class Base36IntTests(SimpleTestCase):
    def test_roundtrip(self):
        for n in [0, 1, 1000, 1000000]:
            self.assertEqual(n, base36_to_int(int_to_base36(n)))

    def test_negative_input(self):
        with self.assertRaisesMessage(ValueError, "Negative base36 conversion input."):
            int_to_base36(-1)

    def test_to_base36_errors(self):
        for n in ["1", "foo", {1: 2}, (1, 2, 3), 3.141]:
            with self.assertRaises(TypeError):
                int_to_base36(n)

    def test_invalid_literal(self):
        for n in ["#", " "]:
            with self.assertRaisesMessage(
                ValueError, "invalid literal for int() with base 36: '%s'" % n
            ):
                base36_to_int(n)

    def test_input_too_large(self):
        with self.assertRaisesMessage(ValueError, "Base36 input too large"):
            base36_to_int("1" * 14)

    def test_to_int_errors(self):
        for n in [123, {1: 2}, (1, 2, 3), 3.141]:
            with self.assertRaises(TypeError):
                base36_to_int(n)

    def test_values(self):
        for n, b36 in [(0, "0"), (1, "1"), (42, "16"), (818469960, "django")]:
            self.assertEqual(int_to_base36(n), b36)
            self.assertEqual(base36_to_int(b36), n)


class URLHasAllowedHostAndSchemeTests(unittest.TestCase):
    def test_bad_urls(self):
        bad_urls = (
            "http://example.com",
            "http:///example.com",
            "https://example.com",
            "ftp://example.com",
            r"\\example.com",
            r"\\\example.com",
            r"/\\/example.com",
            r"\\\example.com",
            r"\\example.com",
            r"\\//example.com",
            r"/\/example.com",
            r"\/example.com",
            r"/\example.com",
            "http:///example.com",
            r"http:/\//example.com",
            r"http:\/example.com",
            r"http:/\example.com",
            'javascript:alert("XSS")',
            "\njavascript:alert(x)",
            "\x08//example.com",
            r"http://otherserver\@example.com",
            r"http:\\testserver\@example.com",
            r"http://testserver\me:pass@example.com",
            r"http://testserver\@example.com",
            r"http:\\testserver\confirm\me@example.com",
            "http:999999999",
            "ftp:9999999999",
            "\n",
            "http://[2001:cdba:0000:0000:0000:0000:3257:9652/",
            "http://2001:cdba:0000:0000:0000:0000:3257:9652]/",
        )
        for bad_url in bad_urls:
            with self.subTest(url=bad_url):
                self.assertIs(
                    url_has_allowed_host_and_scheme(
                        bad_url, allowed_hosts={"testserver", "testserver2"}
                    ),
                    False,
                )

    def test_good_urls(self):
        good_urls = (
            "/view/?param=http://example.com",
            "/view/?param=https://example.com",
            "/view?param=ftp://example.com",
            "view/?param=//example.com",
            "https://testserver/",
            "HTTPS://testserver/",
            "//testserver/",
            "http://testserver/confirm?email=me@example.com",
            "/url%20with%20spaces/",
            "path/http:2222222222",
        )
        for good_url in good_urls:
            with self.subTest(url=good_url):
                self.assertIs(
                    url_has_allowed_host_and_scheme(
                        good_url, allowed_hosts={"otherserver", "testserver"}
                    ),
                    True,
                )

    def test_basic_auth(self):
        # Valid basic auth credentials are allowed.
        self.assertIs(
            url_has_allowed_host_and_scheme(
                r"http://user:pass@testserver/", allowed_hosts={"user:pass@testserver"}
            ),
            True,
        )

    def test_no_allowed_hosts(self):
        # A path without host is allowed.
        self.assertIs(
            url_has_allowed_host_and_scheme(
                "/confirm/me@example.com", allowed_hosts=None
            ),
            True,
        )
        # Basic auth without host is not allowed.
        self.assertIs(
            url_has_allowed_host_and_scheme(
                r"http://testserver\@example.com", allowed_hosts=None
            ),
            False,
        )

    def test_allowed_hosts_str(self):
        self.assertIs(
            url_has_allowed_host_and_scheme(
                "http://good.com/good", allowed_hosts="good.com"
            ),
            True,
        )
        self.assertIs(
            url_has_allowed_host_and_scheme(
                "http://good.co/evil", allowed_hosts="good.com"
            ),
            False,
        )

    def test_secure_param_https_urls(self):
        secure_urls = (
            "https://example.com/p",
            "HTTPS://example.com/p",
            "/view/?param=http://example.com",
        )
        for url in secure_urls:
            with self.subTest(url=url):
                self.assertIs(
                    url_has_allowed_host_and_scheme(
                        url, allowed_hosts={"example.com"}, require_https=True
                    ),
                    True,
                )

    def test_secure_param_non_https_urls(self):
        insecure_urls = (
            "http://example.com/p",
            "ftp://example.com/p",
            "//example.com/p",
        )
        for url in insecure_urls:
            with self.subTest(url=url):
                self.assertIs(
                    url_has_allowed_host_and_scheme(
                        url, allowed_hosts={"example.com"}, require_https=True
                    ),
                    False,
                )


class URLSafeBase64Tests(unittest.TestCase):
    def test_roundtrip(self):
        bytestring = b"foo"
        encoded = urlsafe_base64_encode(bytestring)
        decoded = urlsafe_base64_decode(encoded)
        self.assertEqual(bytestring, decoded)


class IsSameDomainTests(unittest.TestCase):
    def test_good(self):
        for pair in (
            ("example.com", "example.com"),
            ("example.com", ".example.com"),
            ("foo.example.com", ".example.com"),
            ("example.com:8888", "example.com:8888"),
            ("example.com:8888", ".example.com:8888"),
            ("foo.example.com:8888", ".example.com:8888"),
        ):
            self.assertIs(is_same_domain(*pair), True)

    def test_bad(self):
        for pair in (
            ("example2.com", "example.com"),
            ("foo.example.com", "example.com"),
            ("example.com:9999", "example.com:8888"),
            ("foo.example.com:8888", ""),
        ):
            self.assertIs(is_same_domain(*pair), False)


class ETagProcessingTests(unittest.TestCase):
    def test_parsing(self):
        self.assertEqual(
            parse_etags(r'"" ,  "etag", "e\\tag", W/"weak"'),
            ['""', '"etag"', r'"e\\tag"', 'W/"weak"'],
        )
        self.assertEqual(parse_etags("*"), ["*"])

        # Ignore RFC 2616 ETags that are invalid according to RFC 7232.
        self.assertEqual(parse_etags(r'"etag", "e\"t\"ag"'), ['"etag"'])

    def test_quoting(self):
        self.assertEqual(quote_etag("etag"), '"etag"')  # unquoted
        self.assertEqual(quote_etag('"etag"'), '"etag"')  # quoted
        self.assertEqual(quote_etag('W/"etag"'), 'W/"etag"')  # quoted, weak


class HttpDateProcessingTests(unittest.TestCase):
    def test_http_date(self):
        t = 1167616461.0
        self.assertEqual(http_date(t), "Mon, 01 Jan 2007 01:54:21 GMT")

    def test_parsing_rfc1123(self):
        parsed = parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT")
        self.assertEqual(
            datetime.fromtimestamp(parsed, timezone.utc),
            datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc),
        )

    @unittest.skipIf(platform.architecture()[0] == "32bit", "The Year 2038 problem.")
    @mock.patch("django.utils.http.datetime.datetime")
    def test_parsing_rfc850(self, mocked_datetime):
        mocked_datetime.side_effect = datetime
        mocked_datetime.now = mock.Mock()
        now_1 = datetime(2019, 11, 6, 8, 49, 37, tzinfo=timezone.utc)
        now_2 = datetime(2020, 11, 6, 8, 49, 37, tzinfo=timezone.utc)
        now_3 = datetime(2048, 11, 6, 8, 49, 37, tzinfo=timezone.utc)
        tests = (
            (
                now_1,
                "Tuesday, 31-Dec-69 08:49:37 GMT",
                datetime(2069, 12, 31, 8, 49, 37, tzinfo=timezone.utc),
            ),
            (
                now_1,
                "Tuesday, 10-Nov-70 08:49:37 GMT",
                datetime(1970, 11, 10, 8, 49, 37, tzinfo=timezone.utc),
            ),
            (
                now_1,
                "Sunday, 06-Nov-94 08:49:37 GMT",
                datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc),
            ),
            (
                now_2,
                "Wednesday, 31-Dec-70 08:49:37 GMT",
                datetime(2070, 12, 31, 8, 49, 37, tzinfo=timezone.utc),
            ),
            (
                now_2,
                "Friday, 31-Dec-71 08:49:37 GMT",
                datetime(1971, 12, 31, 8, 49, 37, tzinfo=timezone.utc),
            ),
            (
                now_3,
                "Sunday, 31-Dec-00 08:49:37 GMT",
                datetime(2000, 12, 31, 8, 49, 37, tzinfo=timezone.utc),
            ),
            (
                now_3,
                "Friday, 31-Dec-99 08:49:37 GMT",
                datetime(1999, 12, 31, 8, 49, 37, tzinfo=timezone.utc),
            ),
        )
        for now, rfc850str, expected_date in tests:
            with self.subTest(rfc850str=rfc850str):
                mocked_datetime.now.return_value = now
                parsed = parse_http_date(rfc850str)
                mocked_datetime.now.assert_called_once_with(tz=timezone.utc)
                self.assertEqual(
                    datetime.fromtimestamp(parsed, timezone.utc),
                    expected_date,
                )
            mocked_datetime.reset_mock()

    def test_parsing_asctime(self):
        parsed = parse_http_date("Sun Nov  6 08:49:37 1994")
        self.assertEqual(
            datetime.fromtimestamp(parsed, timezone.utc),
            datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc),
        )

    def test_parsing_asctime_nonascii_digits(self):
        """Non-ASCII unicode decimals raise an error."""
        with self.assertRaises(ValueError):
            parse_http_date("Sun Nov  6 08:49:37 １９９４")
        with self.assertRaises(ValueError):
            parse_http_date("Sun Nov １２ 08:49:37 1994")

    def test_parsing_year_less_than_70(self):
        parsed = parse_http_date("Sun Nov  6 08:49:37 0037")
        self.assertEqual(
            datetime.fromtimestamp(parsed, timezone.utc),
            datetime(2037, 11, 6, 8, 49, 37, tzinfo=timezone.utc),
        )


class EscapeLeadingSlashesTests(unittest.TestCase):
    def test(self):
        tests = (
            ("//example.com", "/%2Fexample.com"),
            ("//", "/%2F"),
        )
        for url, expected in tests:
            with self.subTest(url=url):
                self.assertEqual(escape_leading_slashes(url), expected)


class ParseHeaderParameterTests(unittest.TestCase):
    def test_basic(self):
        tests = [
            ("text/plain", ("text/plain", {})),
            ("text/vnd.just.made.this.up ; ", ("text/vnd.just.made.this.up", {})),
            ("text/plain;charset=us-ascii", ("text/plain", {"charset": "us-ascii"})),
            (
                'text/plain ; charset="us-ascii"',
                ("text/plain", {"charset": "us-ascii"}),
            ),
            (
                'text/plain ; charset="us-ascii"; another=opt',
                ("text/plain", {"charset": "us-ascii", "another": "opt"}),
            ),
            (
                'attachment; filename="silly.txt"',
                ("attachment", {"filename": "silly.txt"}),
            ),
            (
                'attachment; filename="strange;name"',
                ("attachment", {"filename": "strange;name"}),
            ),
            (
                'attachment; filename="strange;name";size=123;',
                ("attachment", {"filename": "strange;name", "size": "123"}),
            ),
            (
                'form-data; name="files"; filename="fo\\"o;bar"',
                ("form-data", {"name": "files", "filename": 'fo"o;bar'}),
            ),
        ]
        for header, expected in tests:
            with self.subTest(header=header):
                self.assertEqual(parse_header_parameters(header), expected)

    def test_rfc2231_parsing(self):
        test_data = (
            (
                "Content-Type: application/x-stuff; "
                "title*=us-ascii'en-us'This%20is%20%2A%2A%2Afun%2A%2A%2A",
                "This is ***fun***",
            ),
            (
                "Content-Type: application/x-stuff; title*=UTF-8''foo-%c3%a4.html",
                "foo-ä.html",
            ),
            (
                "Content-Type: application/x-stuff; title*=iso-8859-1''foo-%E4.html",
                "foo-ä.html",
            ),
        )
        for raw_line, expected_title in test_data:
            parsed = parse_header_parameters(raw_line)
            self.assertEqual(parsed[1]["title"], expected_title)

    def test_rfc2231_wrong_title(self):
        """
        Test wrongly formatted RFC 2231 headers (missing double single quotes).
        Parsing should not crash (#24209).
        """
        test_data = (
            (
                "Content-Type: application/x-stuff; "
                "title*='This%20is%20%2A%2A%2Afun%2A%2A%2A",
                "'This%20is%20%2A%2A%2Afun%2A%2A%2A",
            ),
            ("Content-Type: application/x-stuff; title*='foo.html", "'foo.html"),
            ("Content-Type: application/x-stuff; title*=bar.html", "bar.html"),
        )
        for raw_line, expected_title in test_data:
            parsed = parse_header_parameters(raw_line)
            self.assertEqual(parsed[1]["title"], expected_title)
