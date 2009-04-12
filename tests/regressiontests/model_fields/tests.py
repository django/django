import datetime
import unittest

import django.test
from django import forms
from django.db import models
from django.core.exceptions import ValidationError

from models import Foo, Bar, Whiz, BigD, BigS

try:
    from decimal import Decimal
except ImportError:
    from django.utils._decimal import Decimal

class DecimalFieldTests(django.test.TestCase):
    def test_to_python(self):
        f = models.DecimalField(max_digits=4, decimal_places=2)
        self.assertEqual(f.to_python(3), Decimal("3"))
        self.assertEqual(f.to_python("3.14"), Decimal("3.14"))
        self.assertRaises(ValidationError, f.to_python, "abc")

    def test_default(self):
        f = models.DecimalField(default=Decimal("0.00"))
        self.assertEqual(f.get_default(), Decimal("0.00"))

    def test_format(self):
        f = models.DecimalField(max_digits=5, decimal_places=1)
        self.assertEqual(f._format(f.to_python(2)), u'2.0')
        self.assertEqual(f._format(f.to_python('2.6')), u'2.6')
        self.assertEqual(f._format(None), None)

    def test_get_db_prep_lookup(self):
        f = models.DecimalField(max_digits=5, decimal_places=1)
        self.assertEqual(f.get_db_prep_lookup('exact', None), [None])

    def test_filter_with_strings(self):
        """
        We should be able to filter decimal fields using strings (#8023)
        """
        Foo.objects.create(id=1, a='abc', d=Decimal("12.34"))
        self.assertEqual(list(Foo.objects.filter(d=u'1.23')), [])

    def test_save_without_float_conversion(self):
        """
        Ensure decimals don't go through a corrupting float conversion during
        save (#5079).
        """
        bd = BigD(d="12.9")
        bd.save()
        bd = BigD.objects.get(pk=bd.pk)
        self.assertEqual(bd.d, Decimal("12.9"))

    def test_lookup_really_big_value(self):
        """
        Ensure that really big values can be used in a filter statement, even
        with older Python versions.
        """
        # This should not crash. That counts as a win for our purposes.
        Foo.objects.filter(d__gte=100000000000)

class ForeignKeyTests(django.test.TestCase):
    def test_callable_default(self):
        """Test the use of a lazy callable for ForeignKey.default"""
        a = Foo.objects.create(id=1, a='abc', d=Decimal("12.34"))
        b = Bar.objects.create(b="bcd")
        self.assertEqual(b.a, a)

class DateTimeFieldTests(unittest.TestCase):
    def test_datetimefield_to_python_usecs(self):
        """DateTimeField.to_python should support usecs"""
        f = models.DateTimeField()
        self.assertEqual(f.to_python('2001-01-02 03:04:05.000006'),
                         datetime.datetime(2001, 1, 2, 3, 4, 5, 6))
        self.assertEqual(f.to_python('2001-01-02 03:04:05.999999'),
                         datetime.datetime(2001, 1, 2, 3, 4, 5, 999999))

    def test_timefield_to_python_usecs(self):
        """TimeField.to_python should support usecs"""
        f = models.TimeField()
        self.assertEqual(f.to_python('01:02:03.000004'),
                         datetime.time(1, 2, 3, 4))
        self.assertEqual(f.to_python('01:02:03.999999'),
                         datetime.time(1, 2, 3, 999999))

class BooleanFieldTests(unittest.TestCase):
    def _test_get_db_prep_lookup(self, f):
        self.assertEqual(f.get_db_prep_lookup('exact', True), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', '1'), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', 1), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', False), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', '0'), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', 0), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', None), [None])

    def test_booleanfield_get_db_prep_lookup(self):
        self._test_get_db_prep_lookup(models.BooleanField())

    def test_nullbooleanfield_get_db_prep_lookup(self):
        self._test_get_db_prep_lookup(models.NullBooleanField())

    def test_booleanfield_choices_blank(self):
        """
        Test that BooleanField with choices and defaults doesn't generate a
        formfield with the blank option (#9640, #10549).
        """
        choices = [(1, u'Si'), (2, 'No')]
        f = models.BooleanField(choices=choices, default=1, null=True)
        self.assertEqual(f.formfield().choices, [('', '---------')] + choices)

        f = models.BooleanField(choices=choices, default=1, null=False)
        self.assertEqual(f.formfield().choices, choices)

class ChoicesTests(django.test.TestCase):
    def test_choices_and_field_display(self):
        """
        Check that get_choices and get_flatchoices interact with
        get_FIELD_display to return the expected values (#7913).
        """
        self.assertEqual(Whiz(c=1).get_c_display(), 'First')    # A nested value
        self.assertEqual(Whiz(c=0).get_c_display(), 'Other')    # A top level value
        self.assertEqual(Whiz(c=9).get_c_display(), 9)          # Invalid value
        self.assertEqual(Whiz(c=None).get_c_display(), None)    # Blank value
        self.assertEqual(Whiz(c='').get_c_display(), '')        # Empty value

class SlugFieldTests(django.test.TestCase):
    def test_slugfield_max_length(self):
        """
        Make sure SlugField honors max_length (#9706)
        """
        bs = BigS.objects.create(s = 'slug'*50)
        bs = BigS.objects.get(pk=bs.pk)
        self.assertEqual(bs.s, 'slug'*50)

