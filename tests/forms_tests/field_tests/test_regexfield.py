# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.forms import RegexField, ValidationError
from django.test import SimpleTestCase
from django.utils import six


class RegexFieldTest(SimpleTestCase):

    def test_regexfield_1(self):
        f = RegexField('^[0-9][A-F][0-9]$')
        self.assertEqual('2A2', f.clean('2A2'))
        self.assertEqual('3F3', f.clean('3F3'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean('3G3')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean(' 2A2')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean('2A2 ')
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean('')

    def test_regexfield_2(self):
        f = RegexField('^[0-9][A-F][0-9]$', required=False)
        self.assertEqual('2A2', f.clean('2A2'))
        self.assertEqual('3F3', f.clean('3F3'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean('3G3')
        self.assertEqual('', f.clean(''))

    def test_regexfield_3(self):
        f = RegexField(re.compile('^[0-9][A-F][0-9]$'))
        self.assertEqual('2A2', f.clean('2A2'))
        self.assertEqual('3F3', f.clean('3F3'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean('3G3')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean(' 2A2')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean('2A2 ')

    def test_regexfield_4(self):
        f = RegexField('^[0-9]+$', min_length=5, max_length=10)
        with self.assertRaisesMessage(ValidationError, "'Ensure this value has at least 5 characters (it has 3).'"):
            f.clean('123')
        six.assertRaisesRegex(
            self, ValidationError,
            "'Ensure this value has at least 5 characters \(it has 3\)\.',"
            " u?'Enter a valid value\.'",
            f.clean, 'abc'
        )
        self.assertEqual('12345', f.clean('12345'))
        self.assertEqual('1234567890', f.clean('1234567890'))
        with self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 10 characters (it has 11).'"):
            f.clean('12345678901')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean('12345a')

    def test_regexfield_unicode_characters(self):
        f = RegexField('^\w+$')
        self.assertEqual('éèøçÎÎ你好', f.clean('éèøçÎÎ你好'))

    def test_change_regex_after_init(self):
        f = RegexField('^[a-z]+$')
        f.regex = '^[0-9]+$'
        self.assertEqual('1234', f.clean('1234'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid value.'"):
            f.clean('abcd')
