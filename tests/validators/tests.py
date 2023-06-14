import re
import types
from datetime import datetime, timedelta
from decimal import Decimal
from unittest import TestCase, mock

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import (
    BaseValidator,
    DecimalValidator,
    EmailValidator,
    FileExtensionValidator,
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    ProhibitNullCharactersValidator,
    RegexValidator,
    StepValueValidator,
    URLValidator,
    int_list_validator,
    validate_comma_separated_integer_list,
    validate_email,
    validate_image_file_extension,
    validate_integer,
    validate_ipv4_address,
    validate_ipv6_address,
    validate_ipv46_address,
    validate_slug,
    validate_unicode_slug,
)
from django.test import SimpleTestCase

try:
    from PIL import Image  # noqa
except ImportError:
    PILLOW_IS_INSTALLED = False
else:
    PILLOW_IS_INSTALLED = True

NOW = datetime.now()
EXTENDED_SCHEMES = ["http", "https", "ftp", "ftps", "git", "file", "git+ssh"]

VALID_URLS = [
    "http://www.djangoproject.com/",
    "HTTP://WWW.DJANGOPROJECT.COM/",
    "http://localhost/",
    "http://example.com/",
    "http://example.com:0",
    "http://example.com:0/",
    "http://example.com:65535",
    "http://example.com:65535/",
    "http://example.com./",
    "http://www.example.com/",
    "http://www.example.com:8000/test",
    "http://valid-with-hyphens.com/",
    "http://subdomain.example.com/",
    "http://a.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://200.8.9.10/",
    "http://200.8.9.10:8000/test",
    "http://su--b.valid-----hyphens.com/",
    "http://example.com?something=value",
    "http://example.com/index.php?something=value&another=value2",
    "https://example.com/",
    "ftp://example.com/",
    "ftps://example.com/",
    "http://foo.com/blah_blah",
    "http://foo.com/blah_blah/",
    "http://foo.com/blah_blah_(wikipedia)",
    "http://foo.com/blah_blah_(wikipedia)_(again)",
    "http://www.example.com/wpstyle/?p=364",
    "https://www.example.com/foo/?bar=baz&inga=42&quux",
    "http://✪df.ws/123",
    "http://userid@example.com",
    "http://userid@example.com/",
    "http://userid@example.com:8080",
    "http://userid@example.com:8080/",
    "http://userid@example.com:65535",
    "http://userid@example.com:65535/",
    "http://userid:@example.com",
    "http://userid:@example.com/",
    "http://userid:@example.com:8080",
    "http://userid:@example.com:8080/",
    "http://userid:password@example.com",
    "http://userid:password@example.com/",
    "http://userid:password@example.com:8",
    "http://userid:password@example.com:8/",
    "http://userid:password@example.com:8080",
    "http://userid:password@example.com:8080/",
    "http://userid:password@example.com:65535",
    "http://userid:password@example.com:65535/",
    "https://userid:paaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaassword@example.com",
    "https://userid:paaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaassword@example.com:8080",
    "https://useridddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "dddddddddddddddddddddd:password@example.com",
    "https://useridddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddd:password@example.com:8080",
    "http://userid:password" + "d" * 2000 + "@example.aaaaaaaaaaaaa.com",
    "http://142.42.1.1/",
    "http://142.42.1.1:8080/",
    "http://➡.ws/䨹",
    "http://⌘.ws",
    "http://⌘.ws/",
    "http://foo.com/blah_(wikipedia)#cite-1",
    "http://foo.com/blah_(wikipedia)_blah#cite-1",
    "http://foo.com/unicode_(✪)_in_parens",
    "http://foo.com/(something)?after=parens",
    "http://☺.damowmow.com/",
    "http://djangoproject.com/events/#&product=browser",
    "http://j.mp",
    "ftp://foo.bar/baz",
    "http://foo.bar/?q=Test%20URL-encoded%20stuff",
    "http://مثال.إختبار",
    "http://例子.测试",
    "http://उदाहरण.परीक्षा",
    "http://-.~_!$&'()*+,;=%40:80%2f@example.com",
    "http://xn--7sbb4ac0ad0be6cf.xn--p1ai",
    "http://1337.net",
    "http://a.b-c.de",
    "http://223.255.255.254",
    "ftps://foo.bar/",
    "http://10.1.1.254",
    "http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html",
    "http://[::192.9.5.5]/ipng",
    "http://[::ffff:192.9.5.5]/ipng",
    "http://[::1]:8080/",
    "http://0.0.0.0/",
    "http://255.255.255.255",
    "http://224.0.0.0",
    "http://224.1.1.1",
    "http://111.112.113.114/",
    "http://88.88.88.88/",
    "http://11.12.13.14/",
    "http://10.20.30.40/",
    "http://1.2.3.4/",
    "http://127.0.01.09.home.lan",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.ex"
    "ample.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaa.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://dashintld.c-m",
    "http://multipledashintld.a-b-c",
    "http://evenmoredashintld.a---c",
    "http://dashinpunytld.xn---c",
]

INVALID_URLS = [
    None,
    56,
    "no_scheme",
    "foo",
    "http://",
    "http://example",
    "http://example.",
    "http://example.com:-1",
    "http://example.com:-1/",
    "http://example.com:000000080",
    "http://example.com:000000080/",
    "http://.com",
    "http://invalid-.com",
    "http://-invalid.com",
    "http://invalid.com-",
    "http://invalid.-com",
    "http://inv-.alid-.com",
    "http://inv-.-alid.com",
    "file://localhost/path",
    "git://example.com/",
    "http://.",
    "http://..",
    "http://../",
    "http://?",
    "http://??",
    "http://??/",
    "http://#",
    "http://##",
    "http://##/",
    "http://foo.bar?q=Spaces should be encoded",
    "//",
    "//a",
    "///a",
    "///",
    "http:///a",
    "foo.com",
    "rdar://1234",
    "h://test",
    "http:// shouldfail.com",
    ":// should fail",
    "http://foo.bar/foo(bar)baz quux",
    "http://-error-.invalid/",
    "http://dashinpunytld.trailingdot.xn--.",
    "http://dashinpunytld.xn---",
    "http://-a.b.co",
    "http://a.b-.co",
    "http://a.-b.co",
    "http://a.b-.c.co",
    "http:/",
    "http://",
    "http://",
    "http://1.1.1.1.1",
    "http://123.123.123",
    "http://3628126748",
    "http://123",
    "http://000.000.000.000",
    "http://016.016.016.016",
    "http://192.168.000.001",
    "http://01.2.3.4",
    "http://01.2.3.4",
    "http://1.02.3.4",
    "http://1.2.03.4",
    "http://1.2.3.04",
    "http://.www.foo.bar/",
    "http://.www.foo.bar./",
    "http://[::1:2::3]:8/",
    "http://[::1:2::3]:8080/",
    "http://[]",
    "http://[]:8080",
    "http://example..com/",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.e"
    "xample.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaa.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaa",
    "http://example." + ("a" * 63 + ".") * 1000 + "com",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaa."
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaa",
    "https://test.[com",
    "http://@example.com",
    "http://:@example.com",
    "http://:bar@example.com",
    "http://foo@bar@example.com",
    "http://foo/bar@example.com",
    "http://foo:bar:baz@example.com",
    "http://foo:bar@baz@example.com",
    "http://foo:bar/baz@example.com",
    "http://invalid-.com/?m=foo@example.com",
    # Newlines and tabs are not accepted.
    "http://www.djangoproject.com/\n",
    "http://[::ffff:192.9.5.5]\n",
    "http://www.djangoproject.com/\r",
    "http://[::ffff:192.9.5.5]\r",
    "http://www.django\rproject.com/",
    "http://[::\rffff:192.9.5.5]",
    "http://\twww.djangoproject.com/",
    "http://\t[::ffff:192.9.5.5]",
    # Trailing junk does not take forever to reject.
    "http://www.asdasdasdasdsadfm.com.br ",
    "http://www.asdasdasdasdsadfm.com.br z",
]

TEST_DATA = [
    # (validator, value, expected),
    (validate_integer, "42", None),
    (validate_integer, "-42", None),
    (validate_integer, -42, None),
    (validate_integer, -42.5, ValidationError),
    (validate_integer, None, ValidationError),
    (validate_integer, "a", ValidationError),
    (validate_integer, "\n42", ValidationError),
    (validate_integer, "42\n", ValidationError),
    (validate_email, "email@here.com", None),
    (validate_email, "weirder-email@here.and.there.com", None),
    (validate_email, "email@[127.0.0.1]", None),
    (validate_email, "email@[2001:dB8::1]", None),
    (validate_email, "email@[2001:dB8:0:0:0:0:0:1]", None),
    (validate_email, "email@[::fffF:127.0.0.1]", None),
    (validate_email, "example@valid-----hyphens.com", None),
    (validate_email, "example@valid-with-hyphens.com", None),
    (validate_email, "test@domain.with.idn.tld.उदाहरण.परीक्षा", None),
    (validate_email, "email@localhost", None),
    (EmailValidator(allowlist=["localdomain"]), "email@localdomain", None),
    (validate_email, '"test@test"@example.com', None),
    (validate_email, "example@atm.%s" % ("a" * 63), None),
    (validate_email, "example@%s.atm" % ("a" * 63), None),
    (validate_email, "example@%s.%s.atm" % ("a" * 63, "b" * 10), None),
    (validate_email, "example@atm.%s" % ("a" * 64), ValidationError),
    (validate_email, "example@%s.atm.%s" % ("b" * 64, "a" * 63), ValidationError),
    (validate_email, "example@%scom" % (("a" * 63 + ".") * 100), ValidationError),
    (validate_email, None, ValidationError),
    (validate_email, "", ValidationError),
    (validate_email, "abc", ValidationError),
    (validate_email, "abc@", ValidationError),
    (validate_email, "abc@bar", ValidationError),
    (validate_email, "a @x.cz", ValidationError),
    (validate_email, "abc@.com", ValidationError),
    (validate_email, "something@@somewhere.com", ValidationError),
    (validate_email, "email@127.0.0.1", ValidationError),
    (validate_email, "email@[127.0.0.256]", ValidationError),
    (validate_email, "email@[2001:db8::12345]", ValidationError),
    (validate_email, "email@[2001:db8:0:0:0:0:1]", ValidationError),
    (validate_email, "email@[::ffff:127.0.0.256]", ValidationError),
    (validate_email, "email@[2001:dg8::1]", ValidationError),
    (validate_email, "email@[2001:dG8:0:0:0:0:0:1]", ValidationError),
    (validate_email, "email@[::fTzF:127.0.0.1]", ValidationError),
    (validate_email, "example@invalid-.com", ValidationError),
    (validate_email, "example@-invalid.com", ValidationError),
    (validate_email, "example@invalid.com-", ValidationError),
    (validate_email, "example@inv-.alid-.com", ValidationError),
    (validate_email, "example@inv-.-alid.com", ValidationError),
    (validate_email, 'test@example.com\n\n<script src="x.js">', ValidationError),
    # Quoted-string format (CR not allowed)
    (validate_email, '"\\\011"@here.com', None),
    (validate_email, '"\\\012"@here.com', ValidationError),
    (validate_email, "trailingdot@shouldfail.com.", ValidationError),
    # Max length of domain name labels is 63 characters per RFC 1034.
    (validate_email, "a@%s.us" % ("a" * 63), None),
    (validate_email, "a@%s.us" % ("a" * 64), ValidationError),
    # Trailing newlines in username or domain not allowed
    (validate_email, "a@b.com\n", ValidationError),
    (validate_email, "a\n@b.com", ValidationError),
    (validate_email, '"test@test"\n@example.com', ValidationError),
    (validate_email, "a@[127.0.0.1]\n", ValidationError),
    (validate_slug, "slug-ok", None),
    (validate_slug, "longer-slug-still-ok", None),
    (validate_slug, "--------", None),
    (validate_slug, "nohyphensoranything", None),
    (validate_slug, "a", None),
    (validate_slug, "1", None),
    (validate_slug, "a1", None),
    (validate_slug, "", ValidationError),
    (validate_slug, " text ", ValidationError),
    (validate_slug, " ", ValidationError),
    (validate_slug, "some@mail.com", ValidationError),
    (validate_slug, "你好", ValidationError),
    (validate_slug, "你 好", ValidationError),
    (validate_slug, "\n", ValidationError),
    (validate_slug, "trailing-newline\n", ValidationError),
    (validate_unicode_slug, "slug-ok", None),
    (validate_unicode_slug, "longer-slug-still-ok", None),
    (validate_unicode_slug, "--------", None),
    (validate_unicode_slug, "nohyphensoranything", None),
    (validate_unicode_slug, "a", None),
    (validate_unicode_slug, "1", None),
    (validate_unicode_slug, "a1", None),
    (validate_unicode_slug, "你好", None),
    (validate_unicode_slug, "", ValidationError),
    (validate_unicode_slug, " text ", ValidationError),
    (validate_unicode_slug, " ", ValidationError),
    (validate_unicode_slug, "some@mail.com", ValidationError),
    (validate_unicode_slug, "\n", ValidationError),
    (validate_unicode_slug, "你 好", ValidationError),
    (validate_unicode_slug, "trailing-newline\n", ValidationError),
    (validate_ipv4_address, "1.1.1.1", None),
    (validate_ipv4_address, "255.0.0.0", None),
    (validate_ipv4_address, "0.0.0.0", None),
    (validate_ipv4_address, "256.1.1.1", ValidationError),
    (validate_ipv4_address, "25.1.1.", ValidationError),
    (validate_ipv4_address, "25,1,1,1", ValidationError),
    (validate_ipv4_address, "25.1 .1.1", ValidationError),
    (validate_ipv4_address, "1.1.1.1\n", ValidationError),
    (validate_ipv4_address, "٧.2٥.3٣.243", ValidationError),
    # Leading zeros are forbidden to avoid ambiguity with the octal notation.
    (validate_ipv4_address, "000.000.000.000", ValidationError),
    (validate_ipv4_address, "016.016.016.016", ValidationError),
    (validate_ipv4_address, "192.168.000.001", ValidationError),
    (validate_ipv4_address, "01.2.3.4", ValidationError),
    (validate_ipv4_address, "01.2.3.4", ValidationError),
    (validate_ipv4_address, "1.02.3.4", ValidationError),
    (validate_ipv4_address, "1.2.03.4", ValidationError),
    (validate_ipv4_address, "1.2.3.04", ValidationError),
    # validate_ipv6_address uses django.utils.ipv6, which
    # is tested in much greater detail in its own testcase
    (validate_ipv6_address, "fe80::1", None),
    (validate_ipv6_address, "::1", None),
    (validate_ipv6_address, "1:2:3:4:5:6:7:8", None),
    (validate_ipv6_address, "1:2", ValidationError),
    (validate_ipv6_address, "::zzz", ValidationError),
    (validate_ipv6_address, "12345::", ValidationError),
    (validate_ipv46_address, "1.1.1.1", None),
    (validate_ipv46_address, "255.0.0.0", None),
    (validate_ipv46_address, "0.0.0.0", None),
    (validate_ipv46_address, "fe80::1", None),
    (validate_ipv46_address, "::1", None),
    (validate_ipv46_address, "1:2:3:4:5:6:7:8", None),
    (validate_ipv46_address, "256.1.1.1", ValidationError),
    (validate_ipv46_address, "25.1.1.", ValidationError),
    (validate_ipv46_address, "25,1,1,1", ValidationError),
    (validate_ipv46_address, "25.1 .1.1", ValidationError),
    (validate_ipv46_address, "1:2", ValidationError),
    (validate_ipv46_address, "::zzz", ValidationError),
    (validate_ipv46_address, "12345::", ValidationError),
    # Leading zeros are forbidden to avoid ambiguity with the octal notation.
    (validate_ipv46_address, "000.000.000.000", ValidationError),
    (validate_ipv46_address, "016.016.016.016", ValidationError),
    (validate_ipv46_address, "192.168.000.001", ValidationError),
    (validate_ipv46_address, "01.2.3.4", ValidationError),
    (validate_ipv46_address, "01.2.3.4", ValidationError),
    (validate_ipv46_address, "1.02.3.4", ValidationError),
    (validate_ipv46_address, "1.2.03.4", ValidationError),
    (validate_ipv46_address, "1.2.3.04", ValidationError),
    (validate_comma_separated_integer_list, "1", None),
    (validate_comma_separated_integer_list, "12", None),
    (validate_comma_separated_integer_list, "1,2", None),
    (validate_comma_separated_integer_list, "1,2,3", None),
    (validate_comma_separated_integer_list, "10,32", None),
    (validate_comma_separated_integer_list, "", ValidationError),
    (validate_comma_separated_integer_list, "a", ValidationError),
    (validate_comma_separated_integer_list, "a,b,c", ValidationError),
    (validate_comma_separated_integer_list, "1, 2, 3", ValidationError),
    (validate_comma_separated_integer_list, ",", ValidationError),
    (validate_comma_separated_integer_list, "1,2,3,", ValidationError),
    (validate_comma_separated_integer_list, "1,2,", ValidationError),
    (validate_comma_separated_integer_list, ",1", ValidationError),
    (validate_comma_separated_integer_list, "1,,2", ValidationError),
    (int_list_validator(sep="."), "1.2.3", None),
    (int_list_validator(sep=".", allow_negative=True), "1.2.3", None),
    (int_list_validator(allow_negative=True), "-1,-2,3", None),
    (int_list_validator(allow_negative=True), "1,-2,-12", None),
    (int_list_validator(), "-1,2,3", ValidationError),
    (int_list_validator(sep="."), "1,2,3", ValidationError),
    (int_list_validator(sep="."), "1.2.3\n", ValidationError),
    (MaxValueValidator(10), 10, None),
    (MaxValueValidator(10), -10, None),
    (MaxValueValidator(10), 0, None),
    (MaxValueValidator(NOW), NOW, None),
    (MaxValueValidator(NOW), NOW - timedelta(days=1), None),
    (MaxValueValidator(0), 1, ValidationError),
    (MaxValueValidator(NOW), NOW + timedelta(days=1), ValidationError),
    (MinValueValidator(-10), -10, None),
    (MinValueValidator(-10), 10, None),
    (MinValueValidator(-10), 0, None),
    (MinValueValidator(NOW), NOW, None),
    (MinValueValidator(NOW), NOW + timedelta(days=1), None),
    (MinValueValidator(0), -1, ValidationError),
    (MinValueValidator(NOW), NOW - timedelta(days=1), ValidationError),
    # limit_value may be a callable.
    (MinValueValidator(lambda: 1), 0, ValidationError),
    (MinValueValidator(lambda: 1), 1, None),
    (StepValueValidator(3), 0, None),
    (MaxLengthValidator(10), "", None),
    (MaxLengthValidator(10), 10 * "x", None),
    (MaxLengthValidator(10), 15 * "x", ValidationError),
    (MinLengthValidator(10), 15 * "x", None),
    (MinLengthValidator(10), 10 * "x", None),
    (MinLengthValidator(10), "", ValidationError),
    (StepValueValidator(3), 1, ValidationError),
    (StepValueValidator(3), 8, ValidationError),
    (StepValueValidator(3), 9, None),
    (StepValueValidator(0.001), 0.55, None),
    (StepValueValidator(0.001), 0.5555, ValidationError),
    (StepValueValidator(Decimal(0.02)), 0.88, None),
    (StepValueValidator(Decimal(0.02)), Decimal(0.88), None),
    (StepValueValidator(Decimal(0.02)), Decimal(0.77), ValidationError),
    (URLValidator(EXTENDED_SCHEMES), "file://localhost/path", None),
    (URLValidator(EXTENDED_SCHEMES), "git://example.com/", None),
    (
        URLValidator(EXTENDED_SCHEMES),
        "git+ssh://git@github.com/example/hg-git.git",
        None,
    ),
    (URLValidator(EXTENDED_SCHEMES), "git://-invalid.com", ValidationError),
    (BaseValidator(True), True, None),
    (BaseValidator(True), False, ValidationError),
    (RegexValidator(), "", None),
    (RegexValidator(), "x1x2", None),
    (RegexValidator("[0-9]+"), "xxxxxx", ValidationError),
    (RegexValidator("[0-9]+"), "1234", None),
    (RegexValidator(re.compile("[0-9]+")), "1234", None),
    (RegexValidator(".*"), "", None),
    (RegexValidator(re.compile(".*")), "", None),
    (RegexValidator(".*"), "xxxxx", None),
    (RegexValidator("x"), "y", ValidationError),
    (RegexValidator(re.compile("x")), "y", ValidationError),
    (RegexValidator("x", inverse_match=True), "y", None),
    (RegexValidator(re.compile("x"), inverse_match=True), "y", None),
    (RegexValidator("x", inverse_match=True), "x", ValidationError),
    (RegexValidator(re.compile("x"), inverse_match=True), "x", ValidationError),
    (RegexValidator("x", flags=re.IGNORECASE), "y", ValidationError),
    (RegexValidator("a"), "A", ValidationError),
    (RegexValidator("a", flags=re.IGNORECASE), "A", None),
    (
        FileExtensionValidator(["txt"]),
        ContentFile("contents", name="fileWithUnsupportedExt.jpg"),
        ValidationError,
    ),
    (
        FileExtensionValidator(["txt"]),
        ContentFile("contents", name="fileWithUnsupportedExt.JPG"),
        ValidationError,
    ),
    (
        FileExtensionValidator(["txt"]),
        ContentFile("contents", name="fileWithNoExtension"),
        ValidationError,
    ),
    (
        FileExtensionValidator([""]),
        ContentFile("contents", name="fileWithAnExtension.txt"),
        ValidationError,
    ),
    (
        FileExtensionValidator([]),
        ContentFile("contents", name="file.txt"),
        ValidationError,
    ),
    (
        FileExtensionValidator([""]),
        ContentFile("contents", name="fileWithNoExtension"),
        None,
    ),
    (FileExtensionValidator(["txt"]), ContentFile("contents", name="file.txt"), None),
    (FileExtensionValidator(["txt"]), ContentFile("contents", name="file.TXT"), None),
    (FileExtensionValidator(["TXT"]), ContentFile("contents", name="file.txt"), None),
    (FileExtensionValidator(), ContentFile("contents", name="file.jpg"), None),
    (DecimalValidator(max_digits=2, decimal_places=2), Decimal("0.99"), None),
    (
        DecimalValidator(max_digits=2, decimal_places=1),
        Decimal("0.99"),
        ValidationError,
    ),
    (DecimalValidator(max_digits=3, decimal_places=1), Decimal("999"), ValidationError),
    (DecimalValidator(max_digits=4, decimal_places=1), Decimal("999"), None),
    (
        DecimalValidator(max_digits=20, decimal_places=2),
        Decimal("742403889818000000"),
        None,
    ),
    (DecimalValidator(20, 2), Decimal("7.42403889818E+17"), None),
    (
        DecimalValidator(max_digits=20, decimal_places=2),
        Decimal("7424742403889818000000"),
        ValidationError,
    ),
    (DecimalValidator(max_digits=5, decimal_places=2), Decimal("7304E-1"), None),
    (
        DecimalValidator(max_digits=5, decimal_places=2),
        Decimal("7304E-3"),
        ValidationError,
    ),
    (DecimalValidator(max_digits=5, decimal_places=5), Decimal("70E-5"), None),
    (
        DecimalValidator(max_digits=5, decimal_places=5),
        Decimal("70E-6"),
        ValidationError,
    ),
    (DecimalValidator(max_digits=2, decimal_places=1), Decimal("0E+1"), None),
    # 'Enter a number.' errors
    *[
        (
            DecimalValidator(decimal_places=2, max_digits=10),
            Decimal(value),
            ValidationError,
        )
        for value in (
            "NaN",
            "-NaN",
            "+NaN",
            "sNaN",
            "-sNaN",
            "+sNaN",
            "Inf",
            "-Inf",
            "+Inf",
            "Infinity",
            "-Infinity",
            "+Infinity",
        )
    ],
    (validate_image_file_extension, ContentFile("contents", name="file.jpg"), None),
    (validate_image_file_extension, ContentFile("contents", name="file.png"), None),
    (validate_image_file_extension, ContentFile("contents", name="file.PNG"), None),
    (
        validate_image_file_extension,
        ContentFile("contents", name="file.txt"),
        ValidationError,
    ),
    (
        validate_image_file_extension,
        ContentFile("contents", name="file"),
        ValidationError,
    ),
    (ProhibitNullCharactersValidator(), "\x00something", ValidationError),
    (ProhibitNullCharactersValidator(), "something", None),
    (ProhibitNullCharactersValidator(), None, None),
]

# Add valid and invalid URL tests.
# This only tests the validator without extended schemes.
TEST_DATA.extend((URLValidator(), url, None) for url in VALID_URLS)
TEST_DATA.extend((URLValidator(), url, ValidationError) for url in INVALID_URLS)


class TestValidators(SimpleTestCase):
    def test_validators(self):
        for validator, value, expected in TEST_DATA:
            name = (
                validator.__name__
                if isinstance(validator, types.FunctionType)
                else validator.__class__.__name__
            )
            exception_expected = expected is not None and issubclass(
                expected, Exception
            )
            with self.subTest(name, value=value):
                if (
                    validator is validate_image_file_extension
                    and not PILLOW_IS_INSTALLED
                ):
                    self.skipTest(
                        "Pillow is required to test validate_image_file_extension."
                    )
                if exception_expected:
                    with self.assertRaises(expected):
                        validator(value)
                else:
                    self.assertEqual(expected, validator(value))

    def test_single_message(self):
        v = ValidationError("Not Valid")
        self.assertEqual(str(v), "['Not Valid']")
        self.assertEqual(repr(v), "ValidationError(['Not Valid'])")

    def test_message_list(self):
        v = ValidationError(["First Problem", "Second Problem"])
        self.assertEqual(str(v), "['First Problem', 'Second Problem']")
        self.assertEqual(
            repr(v), "ValidationError(['First Problem', 'Second Problem'])"
        )

    def test_message_dict(self):
        v = ValidationError({"first": ["First Problem"]})
        self.assertEqual(str(v), "{'first': ['First Problem']}")
        self.assertEqual(repr(v), "ValidationError({'first': ['First Problem']})")

    def test_regex_validator_flags(self):
        msg = "If the flags are set, regex must be a regular expression string."
        with self.assertRaisesMessage(TypeError, msg):
            RegexValidator(re.compile("a"), flags=re.IGNORECASE)

    def test_max_length_validator_message(self):
        v = MaxLengthValidator(
            16, message='"%(value)s" has more than %(limit_value)d characters.'
        )
        with self.assertRaisesMessage(
            ValidationError, '"djangoproject.com" has more than 16 characters.'
        ):
            v("djangoproject.com")


class TestValidatorEquality(TestCase):
    """
    Validators have valid equality operators (#21638)
    """

    def test_regex_equality(self):
        self.assertEqual(
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://"),
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://"),
        )
        self.assertNotEqual(
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://"),
            RegexValidator(r"^(?:[0-9\.\-]*)://"),
        )
        self.assertEqual(
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://", "oh noes", "invalid"),
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://", "oh noes", "invalid"),
        )
        self.assertNotEqual(
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://", "oh", "invalid"),
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://", "oh noes", "invalid"),
        )
        self.assertNotEqual(
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://", "oh noes", "invalid"),
            RegexValidator(r"^(?:[a-z0-9\.\-]*)://"),
        )

        self.assertNotEqual(
            RegexValidator("", flags=re.IGNORECASE),
            RegexValidator(""),
        )

        self.assertNotEqual(
            RegexValidator(""),
            RegexValidator("", inverse_match=True),
        )

    def test_regex_equality_nocache(self):
        pattern = r"^(?:[a-z0-9\.\-]*)://"
        left = RegexValidator(pattern)
        re.purge()
        right = RegexValidator(pattern)

        self.assertEqual(
            left,
            right,
        )

    def test_regex_equality_blank(self):
        self.assertEqual(
            RegexValidator(),
            RegexValidator(),
        )

    def test_email_equality(self):
        self.assertEqual(
            EmailValidator(),
            EmailValidator(),
        )
        self.assertNotEqual(
            EmailValidator(message="BAD EMAIL"),
            EmailValidator(),
        )
        self.assertEqual(
            EmailValidator(message="BAD EMAIL", code="bad"),
            EmailValidator(message="BAD EMAIL", code="bad"),
        )

    def test_basic_equality(self):
        self.assertEqual(
            MaxValueValidator(44),
            MaxValueValidator(44),
        )
        self.assertEqual(MaxValueValidator(44), mock.ANY)
        self.assertEqual(
            StepValueValidator(0.003),
            StepValueValidator(0.003),
        )
        self.assertNotEqual(
            MaxValueValidator(44),
            MinValueValidator(44),
        )
        self.assertNotEqual(
            MinValueValidator(45),
            MinValueValidator(11),
        )
        self.assertNotEqual(
            StepValueValidator(3),
            StepValueValidator(2),
        )

    def test_decimal_equality(self):
        self.assertEqual(
            DecimalValidator(1, 2),
            DecimalValidator(1, 2),
        )
        self.assertNotEqual(
            DecimalValidator(1, 2),
            DecimalValidator(1, 1),
        )
        self.assertNotEqual(
            DecimalValidator(1, 2),
            DecimalValidator(2, 2),
        )
        self.assertNotEqual(
            DecimalValidator(1, 2),
            MinValueValidator(11),
        )

    def test_file_extension_equality(self):
        self.assertEqual(FileExtensionValidator(), FileExtensionValidator())
        self.assertEqual(
            FileExtensionValidator(["txt"]), FileExtensionValidator(["txt"])
        )
        self.assertEqual(
            FileExtensionValidator(["TXT"]), FileExtensionValidator(["txt"])
        )
        self.assertEqual(
            FileExtensionValidator(["TXT", "png"]),
            FileExtensionValidator(["txt", "png"]),
        )
        self.assertEqual(
            FileExtensionValidator(["txt"]),
            FileExtensionValidator(["txt"], code="invalid_extension"),
        )
        self.assertNotEqual(
            FileExtensionValidator(["txt"]), FileExtensionValidator(["png"])
        )
        self.assertNotEqual(
            FileExtensionValidator(["txt"]), FileExtensionValidator(["png", "jpg"])
        )
        self.assertNotEqual(
            FileExtensionValidator(["txt"]),
            FileExtensionValidator(["txt"], code="custom_code"),
        )
        self.assertNotEqual(
            FileExtensionValidator(["txt"]),
            FileExtensionValidator(["txt"], message="custom error message"),
        )

    def test_prohibit_null_characters_validator_equality(self):
        self.assertEqual(
            ProhibitNullCharactersValidator(message="message", code="code"),
            ProhibitNullCharactersValidator(message="message", code="code"),
        )
        self.assertEqual(
            ProhibitNullCharactersValidator(), ProhibitNullCharactersValidator()
        )
        self.assertNotEqual(
            ProhibitNullCharactersValidator(message="message1", code="code"),
            ProhibitNullCharactersValidator(message="message2", code="code"),
        )
        self.assertNotEqual(
            ProhibitNullCharactersValidator(message="message", code="code1"),
            ProhibitNullCharactersValidator(message="message", code="code2"),
        )
