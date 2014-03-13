# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
import re
import types
from unittest import TestCase

from django.core.exceptions import ValidationError
from django.core.validators import (
    BaseValidator, EmailValidator, MaxLengthValidator, MaxValueValidator,
    MinLengthValidator, MinValueValidator, RegexValidator, URLValidator,
    validate_comma_separated_integer_list, validate_email, validate_integer,
    validate_ipv46_address, validate_ipv4_address, validate_ipv6_address,
    validate_slug,
)
from django.test.utils import str_prefix


NOW = datetime.now()
EXTENDED_SCHEMES = ['http', 'https', 'ftp', 'ftps', 'git', 'file']

TEST_DATA = (
    # (validator, value, expected),
    (validate_integer, '42', None),
    (validate_integer, '-42', None),
    (validate_integer, -42, None),
    (validate_integer, -42.5, None),

    (validate_integer, None, ValidationError),
    (validate_integer, 'a', ValidationError),

    (validate_email, 'email@here.com', None),
    (validate_email, 'weirder-email@here.and.there.com', None),
    (validate_email, 'email@[127.0.0.1]', None),
    (validate_email, 'email@[2001:dB8::1]', None),
    (validate_email, 'email@[2001:dB8:0:0:0:0:0:1]', None),
    (validate_email, 'email@[::fffF:127.0.0.1]', None),
    (validate_email, 'example@valid-----hyphens.com', None),
    (validate_email, 'example@valid-with-hyphens.com', None),
    (validate_email, 'test@domain.with.idn.tld.उदाहरण.परीक्षा', None),
    (validate_email, 'email@localhost', None),
    (EmailValidator(whitelist=['localdomain']), 'email@localdomain', None),
    (validate_email, '"test@test"@example.com', None),

    (validate_email, None, ValidationError),
    (validate_email, '', ValidationError),
    (validate_email, 'abc', ValidationError),
    (validate_email, 'abc@', ValidationError),
    (validate_email, 'abc@bar', ValidationError),
    (validate_email, 'a @x.cz', ValidationError),
    (validate_email, 'abc@.com', ValidationError),
    (validate_email, 'something@@somewhere.com', ValidationError),
    (validate_email, 'email@127.0.0.1', ValidationError),
    (validate_email, 'email@[127.0.0.256]', ValidationError),
    (validate_email, 'email@[2001:db8::12345]', ValidationError),
    (validate_email, 'email@[2001:db8:0:0:0:0:1]', ValidationError),
    (validate_email, 'email@[::ffff:127.0.0.256]', ValidationError),
    (validate_email, 'example@invalid-.com', ValidationError),
    (validate_email, 'example@-invalid.com', ValidationError),
    (validate_email, 'example@inv-.alid-.com', ValidationError),
    (validate_email, 'example@inv-.-alid.com', ValidationError),
    (validate_email, 'test@example.com\n\n<script src="x.js">', ValidationError),
    # Quoted-string format (CR not allowed)
    (validate_email, '"\\\011"@here.com', None),
    (validate_email, '"\\\012"@here.com', ValidationError),
    (validate_email, 'trailingdot@shouldfail.com.', ValidationError),

    (validate_slug, 'slug-ok', None),
    (validate_slug, 'longer-slug-still-ok', None),
    (validate_slug, '--------', None),
    (validate_slug, 'nohyphensoranything', None),

    (validate_slug, '', ValidationError),
    (validate_slug, ' text ', ValidationError),
    (validate_slug, ' ', ValidationError),
    (validate_slug, 'some@mail.com', ValidationError),
    (validate_slug, '你好', ValidationError),
    (validate_slug, '\n', ValidationError),

    (validate_ipv4_address, '1.1.1.1', None),
    (validate_ipv4_address, '255.0.0.0', None),
    (validate_ipv4_address, '0.0.0.0', None),

    (validate_ipv4_address, '256.1.1.1', ValidationError),
    (validate_ipv4_address, '25.1.1.', ValidationError),
    (validate_ipv4_address, '25,1,1,1', ValidationError),
    (validate_ipv4_address, '25.1 .1.1', ValidationError),

    # validate_ipv6_address uses django.utils.ipv6, which
    # is tested in much greater detail in it's own testcase
    (validate_ipv6_address, 'fe80::1', None),
    (validate_ipv6_address, '::1', None),
    (validate_ipv6_address, '1:2:3:4:5:6:7:8', None),

    (validate_ipv6_address, '1:2', ValidationError),
    (validate_ipv6_address, '::zzz', ValidationError),
    (validate_ipv6_address, '12345::', ValidationError),

    (validate_ipv46_address, '1.1.1.1', None),
    (validate_ipv46_address, '255.0.0.0', None),
    (validate_ipv46_address, '0.0.0.0', None),
    (validate_ipv46_address, 'fe80::1', None),
    (validate_ipv46_address, '::1', None),
    (validate_ipv46_address, '1:2:3:4:5:6:7:8', None),

    (validate_ipv46_address, '256.1.1.1', ValidationError),
    (validate_ipv46_address, '25.1.1.', ValidationError),
    (validate_ipv46_address, '25,1,1,1', ValidationError),
    (validate_ipv46_address, '25.1 .1.1', ValidationError),
    (validate_ipv46_address, '1:2', ValidationError),
    (validate_ipv46_address, '::zzz', ValidationError),
    (validate_ipv46_address, '12345::', ValidationError),

    (validate_comma_separated_integer_list, '1', None),
    (validate_comma_separated_integer_list, '1,2,3', None),
    (validate_comma_separated_integer_list, '1,2,3,', None),

    (validate_comma_separated_integer_list, '', ValidationError),
    (validate_comma_separated_integer_list, 'a,b,c', ValidationError),
    (validate_comma_separated_integer_list, '1, 2, 3', ValidationError),

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

    (MaxLengthValidator(10), '', None),
    (MaxLengthValidator(10), 10 * 'x', None),

    (MaxLengthValidator(10), 15 * 'x', ValidationError),

    (MinLengthValidator(10), 15 * 'x', None),
    (MinLengthValidator(10), 10 * 'x', None),

    (MinLengthValidator(10), '', ValidationError),

    (URLValidator(), 'http://www.djangoproject.com/', None),
    (URLValidator(), 'HTTP://WWW.DJANGOPROJECT.COM/', None),
    (URLValidator(), 'http://localhost/', None),
    (URLValidator(), 'http://example.com/', None),
    (URLValidator(), 'http://www.example.com/', None),
    (URLValidator(), 'http://www.example.com:8000/test', None),
    (URLValidator(), 'http://valid-with-hyphens.com/', None),
    (URLValidator(), 'http://subdomain.example.com/', None),
    (URLValidator(), 'http://200.8.9.10/', None),
    (URLValidator(), 'http://200.8.9.10:8000/test', None),
    (URLValidator(), 'http://valid-----hyphens.com/', None),
    (URLValidator(), 'http://example.com?something=value', None),
    (URLValidator(), 'http://example.com/index.php?something=value&another=value2', None),
    (URLValidator(), 'https://example.com/', None),
    (URLValidator(), 'ftp://example.com/', None),
    (URLValidator(), 'ftps://example.com/', None),
    (URLValidator(EXTENDED_SCHEMES), 'file://localhost/path', None),
    (URLValidator(EXTENDED_SCHEMES), 'git://example.com/', None),

    (URLValidator(), 'foo', ValidationError),
    (URLValidator(), 'http://', ValidationError),
    (URLValidator(), 'http://example', ValidationError),
    (URLValidator(), 'http://example.', ValidationError),
    (URLValidator(), 'http://.com', ValidationError),
    (URLValidator(), 'http://invalid-.com', ValidationError),
    (URLValidator(), 'http://-invalid.com', ValidationError),
    (URLValidator(), 'http://inv-.alid-.com', ValidationError),
    (URLValidator(), 'http://inv-.-alid.com', ValidationError),
    (URLValidator(), 'file://localhost/path', ValidationError),
    (URLValidator(), 'git://example.com/', ValidationError),
    (URLValidator(EXTENDED_SCHEMES), 'git://-invalid.com', ValidationError),

    (BaseValidator(True), True, None),
    (BaseValidator(True), False, ValidationError),

    (RegexValidator(), '', None),
    (RegexValidator(), 'x1x2', None),
    (RegexValidator('[0-9]+'), 'xxxxxx', ValidationError),
    (RegexValidator('[0-9]+'), '1234', None),
    (RegexValidator(re.compile('[0-9]+')), '1234', None),
    (RegexValidator('.*'), '', None),
    (RegexValidator(re.compile('.*')), '', None),
    (RegexValidator('.*'), 'xxxxx', None),

    (RegexValidator('x'), 'y', ValidationError),
    (RegexValidator(re.compile('x')), 'y', ValidationError),
    (RegexValidator('x', inverse_match=True), 'y', None),
    (RegexValidator(re.compile('x'), inverse_match=True), 'y', None),
    (RegexValidator('x', inverse_match=True), 'x', ValidationError),
    (RegexValidator(re.compile('x'), inverse_match=True), 'x', ValidationError),

    (RegexValidator('x', flags=re.IGNORECASE), 'y', ValidationError),
    (RegexValidator('a'), 'A', ValidationError),
    (RegexValidator('a', flags=re.IGNORECASE), 'A', None),

)


def create_simple_test_method(validator, expected, value, num):
    if expected is not None and issubclass(expected, Exception):
        test_mask = 'test_%s_raises_error_%d'

        def test_func(self):
            # assertRaises not used, so as to be able to produce an error message
            # containing the tested value
            try:
                validator(value)
            except expected:
                pass
            else:
                self.fail("%s not raised when validating '%s'" % (
                    expected.__name__, value))
    else:
        test_mask = 'test_%s_%d'

        def test_func(self):
            try:
                self.assertEqual(expected, validator(value))
            except ValidationError as e:
                self.fail("Validation of '%s' failed. Error message was: %s" % (
                    value, str(e)))
    if isinstance(validator, types.FunctionType):
        val_name = validator.__name__
    else:
        val_name = validator.__class__.__name__
    test_name = test_mask % (val_name, num)
    return test_name, test_func

# Dynamically assemble a test class with the contents of TEST_DATA


class TestSimpleValidators(TestCase):
    def test_single_message(self):
        v = ValidationError('Not Valid')
        self.assertEqual(str(v), str_prefix("[%(_)s'Not Valid']"))
        self.assertEqual(repr(v), str_prefix("ValidationError([%(_)s'Not Valid'])"))

    def test_message_list(self):
        v = ValidationError(['First Problem', 'Second Problem'])
        self.assertEqual(str(v), str_prefix("[%(_)s'First Problem', %(_)s'Second Problem']"))
        self.assertEqual(repr(v), str_prefix("ValidationError([%(_)s'First Problem', %(_)s'Second Problem'])"))

    def test_message_dict(self):
        v = ValidationError({'first': ['First Problem']})
        self.assertEqual(str(v), str_prefix("{%(_)s'first': [%(_)s'First Problem']}"))
        self.assertEqual(repr(v), str_prefix("ValidationError({%(_)s'first': [%(_)s'First Problem']})"))

test_counter = 0
for validator, value, expected in TEST_DATA:
    name, method = create_simple_test_method(validator, expected, value, test_counter)
    setattr(TestSimpleValidators, name, method)
    test_counter += 1


class TestValidatorEquality(TestCase):
    """
    Tests that validators have valid equality operators (#21638)
    """

    def test_regex_equality(self):
        self.assertEqual(
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://'),
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://'),
        )
        self.assertNotEqual(
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://'),
            RegexValidator(r'^(?:[0-9\.\-]*)://'),
        )
        self.assertEqual(
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://', "oh noes", "invalid"),
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://', "oh noes", "invalid"),
        )
        self.assertNotEqual(
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://', "oh", "invalid"),
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://', "oh noes", "invalid"),
        )
        self.assertNotEqual(
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://', "oh noes", "invalid"),
            RegexValidator(r'^(?:[a-z0-9\.\-]*)://'),
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
        self.assertNotEqual(
            MaxValueValidator(44),
            MinValueValidator(44),
        )
        self.assertNotEqual(
            MinValueValidator(45),
            MinValueValidator(11),
        )
