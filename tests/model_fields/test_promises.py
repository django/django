from __future__ import unicode_literals

import datetime
import unittest
from decimal import Decimal

from django.db.models.fields import (
    AutoField, BigIntegerField, BinaryField, BooleanField, CharField,
    CommaSeparatedIntegerField, DateField, DateTimeField, DecimalField,
    EmailField, FilePathField, FloatField, GenericIPAddressField, IntegerField,
    IPAddressField, NullBooleanField, PositiveIntegerField,
    PositiveSmallIntegerField, SlugField, SmallIntegerField, TextField,
    TimeField, URLField,
)
from django.db.models.fields.files import FileField, ImageField
from django.test import SimpleTestCase
from django.utils import six
from django.utils.functional import lazy


class PromiseTest(SimpleTestCase):

    def test_AutoField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(AutoField(primary_key=True).get_prep_value(lazy_func()), int)

    @unittest.skipIf(six.PY3, 'Python 3 has no `long` type.')
    def test_BigIntegerField(self):
        lazy_func = lazy(lambda: long(9999999999999999999), long)  # NOQA: long undefined on PY3
        self.assertIsInstance(BigIntegerField().get_prep_value(lazy_func()), long)  # NOQA

    def test_BinaryField(self):
        lazy_func = lazy(lambda: b'', bytes)
        self.assertIsInstance(BinaryField().get_prep_value(lazy_func()), bytes)

    def test_BooleanField(self):
        lazy_func = lazy(lambda: True, bool)
        self.assertIsInstance(BooleanField().get_prep_value(lazy_func()), bool)

    def test_CharField(self):
        lazy_func = lazy(lambda: '', six.text_type)
        self.assertIsInstance(CharField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(CharField().get_prep_value(lazy_func()), six.text_type)

    def test_CommaSeparatedIntegerField(self):
        lazy_func = lazy(lambda: '1,2', six.text_type)
        self.assertIsInstance(CommaSeparatedIntegerField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(CommaSeparatedIntegerField().get_prep_value(lazy_func()), six.text_type)

    def test_DateField(self):
        lazy_func = lazy(lambda: datetime.date.today(), datetime.date)
        self.assertIsInstance(DateField().get_prep_value(lazy_func()), datetime.date)

    def test_DateTimeField(self):
        lazy_func = lazy(lambda: datetime.datetime.now(), datetime.datetime)
        self.assertIsInstance(DateTimeField().get_prep_value(lazy_func()), datetime.datetime)

    def test_DecimalField(self):
        lazy_func = lazy(lambda: Decimal('1.2'), Decimal)
        self.assertIsInstance(DecimalField().get_prep_value(lazy_func()), Decimal)

    def test_EmailField(self):
        lazy_func = lazy(lambda: 'mailbox@domain.com', six.text_type)
        self.assertIsInstance(EmailField().get_prep_value(lazy_func()), six.text_type)

    def test_FileField(self):
        lazy_func = lazy(lambda: 'filename.ext', six.text_type)
        self.assertIsInstance(FileField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(FileField().get_prep_value(lazy_func()), six.text_type)

    def test_FilePathField(self):
        lazy_func = lazy(lambda: 'tests.py', six.text_type)
        self.assertIsInstance(FilePathField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(FilePathField().get_prep_value(lazy_func()), six.text_type)

    def test_FloatField(self):
        lazy_func = lazy(lambda: 1.2, float)
        self.assertIsInstance(FloatField().get_prep_value(lazy_func()), float)

    def test_ImageField(self):
        lazy_func = lazy(lambda: 'filename.ext', six.text_type)
        self.assertIsInstance(ImageField().get_prep_value(lazy_func()), six.text_type)

    def test_IntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(IntegerField().get_prep_value(lazy_func()), int)

    def test_IPAddressField(self):
        lazy_func = lazy(lambda: '127.0.0.1', six.text_type)
        self.assertIsInstance(IPAddressField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(IPAddressField().get_prep_value(lazy_func()), six.text_type)

    def test_GenericIPAddressField(self):
        lazy_func = lazy(lambda: '127.0.0.1', six.text_type)
        self.assertIsInstance(GenericIPAddressField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(GenericIPAddressField().get_prep_value(lazy_func()), six.text_type)

    def test_NullBooleanField(self):
        lazy_func = lazy(lambda: True, bool)
        self.assertIsInstance(NullBooleanField().get_prep_value(lazy_func()), bool)

    def test_PositiveIntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(PositiveIntegerField().get_prep_value(lazy_func()), int)

    def test_PositiveSmallIntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(PositiveSmallIntegerField().get_prep_value(lazy_func()), int)

    def test_SlugField(self):
        lazy_func = lazy(lambda: 'slug', six.text_type)
        self.assertIsInstance(SlugField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(SlugField().get_prep_value(lazy_func()), six.text_type)

    def test_SmallIntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(SmallIntegerField().get_prep_value(lazy_func()), int)

    def test_TextField(self):
        lazy_func = lazy(lambda: 'Abc', six.text_type)
        self.assertIsInstance(TextField().get_prep_value(lazy_func()), six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(TextField().get_prep_value(lazy_func()), six.text_type)

    def test_TimeField(self):
        lazy_func = lazy(lambda: datetime.datetime.now().time(), datetime.time)
        self.assertIsInstance(TimeField().get_prep_value(lazy_func()), datetime.time)

    def test_URLField(self):
        lazy_func = lazy(lambda: 'http://domain.com', six.text_type)
        self.assertIsInstance(URLField().get_prep_value(lazy_func()), six.text_type)
