import datetime
import unittest

import django.test
from django import forms
from django.db import models
from django.core.exceptions import ValidationError

from models import Foo, Bar, Whiz, BigD, BigS, Image, BigInt, Post, NullBooleanModel, BooleanModel

try:
    from decimal import Decimal
except ImportError:
    from django.utils._decimal import Decimal


# If PIL available, do these tests.
if Image:
    from imagefield import \
            ImageFieldTests, \
            ImageFieldTwoDimensionsTests, \
            ImageFieldNoDimensionsTests, \
            ImageFieldOneDimensionTests, \
            ImageFieldDimensionsFirstTests, \
            ImageFieldUsingFileTests, \
            TwoImageFieldTests


class BasicFieldTests(django.test.TestCase):
    def test_show_hidden_initial(self):
        """
        Regression test for #12913. Make sure fields with choices respect
        show_hidden_initial as a kwarg to models.Field.formfield()
        """
        choices = [(0, 0), (1, 1)]
        model_field = models.Field(choices=choices)
        form_field = model_field.formfield(show_hidden_initial=True)
        self.assertTrue(form_field.show_hidden_initial)

        form_field = model_field.formfield(show_hidden_initial=False)
        self.assertFalse(form_field.show_hidden_initial)

    def test_nullbooleanfield_blank(self):
        """
        Regression test for #13071: NullBooleanField should not throw
        a validation error when given a value of None.

        """
        nullboolean = NullBooleanModel(nbfield=None)
        try:
            nullboolean.full_clean()
        except ValidationError, e:
            self.fail("NullBooleanField failed validation with value of None: %s" % e.messages)

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
        from django.db import connection
        f = models.DecimalField(max_digits=5, decimal_places=1)
        self.assertEqual(f.get_db_prep_lookup('exact', None, connection=connection), [None])

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
        from django.db import connection
        self.assertEqual(f.get_db_prep_lookup('exact', True, connection=connection), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', '1', connection=connection), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', 1, connection=connection), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', False, connection=connection), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', '0', connection=connection), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', 0, connection=connection), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', None, connection=connection), [None])

    def _test_to_python(self, f):
        self.assertTrue(f.to_python(1) is True)
        self.assertTrue(f.to_python(0) is False)

    def test_booleanfield_get_db_prep_lookup(self):
        self._test_get_db_prep_lookup(models.BooleanField())

    def test_nullbooleanfield_get_db_prep_lookup(self):
        self._test_get_db_prep_lookup(models.NullBooleanField())

    def test_booleanfield_to_python(self):
        self._test_to_python(models.BooleanField())

    def test_nullbooleanfield_to_python(self):
        self._test_to_python(models.NullBooleanField())

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

    def test_return_type(self):
        b = BooleanModel()
        b.bfield = True
        b.save()
        b2 = BooleanModel.objects.get(pk=b.pk)
        self.assertTrue(isinstance(b2.bfield, bool))
        self.assertEqual(b2.bfield, True)

        b3 = BooleanModel()
        b3.bfield = False
        b3.save()
        b4 = BooleanModel.objects.get(pk=b3.pk)
        self.assertTrue(isinstance(b4.bfield, bool))
        self.assertEqual(b4.bfield, False)

        b = NullBooleanModel()
        b.nbfield = True
        b.save()
        b2 = NullBooleanModel.objects.get(pk=b.pk)
        self.assertTrue(isinstance(b2.nbfield, bool))
        self.assertEqual(b2.nbfield, True)

        b3 = NullBooleanModel()
        b3.nbfield = False
        b3.save()
        b4 = NullBooleanModel.objects.get(pk=b3.pk)
        self.assertTrue(isinstance(b4.nbfield, bool))
        self.assertEqual(b4.nbfield, False)

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


class ValidationTest(django.test.TestCase):
    def test_charfield_raises_error_on_empty_string(self):
        f = models.CharField()
        self.assertRaises(ValidationError, f.clean, "", None)

    def test_charfield_cleans_empty_string_when_blank_true(self):
        f = models.CharField(blank=True)
        self.assertEqual('', f.clean('', None))

    def test_integerfield_cleans_valid_string(self):
        f = models.IntegerField()
        self.assertEqual(2, f.clean('2', None))

    def test_integerfield_raises_error_on_invalid_intput(self):
        f = models.IntegerField()
        self.assertRaises(ValidationError, f.clean, "a", None)

    def test_charfield_with_choices_cleans_valid_choice(self):
        f = models.CharField(max_length=1, choices=[('a','A'), ('b','B')])
        self.assertEqual('a', f.clean('a', None))

    def test_charfield_with_choices_raises_error_on_invalid_choice(self):
        f = models.CharField(choices=[('a','A'), ('b','B')])
        self.assertRaises(ValidationError, f.clean, "not a", None)

    def test_choices_validation_supports_named_groups(self):
        f = models.IntegerField(choices=(('group',((10,'A'),(20,'B'))),(30,'C')))
        self.assertEqual(10, f.clean(10, None))

    def test_nullable_integerfield_raises_error_with_blank_false(self):
        f = models.IntegerField(null=True, blank=False)
        self.assertRaises(ValidationError, f.clean, None, None)

    def test_nullable_integerfield_cleans_none_on_null_and_blank_true(self):
        f = models.IntegerField(null=True, blank=True)
        self.assertEqual(None, f.clean(None, None))

    def test_integerfield_raises_error_on_empty_input(self):
        f = models.IntegerField(null=False)
        self.assertRaises(ValidationError, f.clean, None, None)
        self.assertRaises(ValidationError, f.clean, '', None)

    def test_charfield_raises_error_on_empty_input(self):
        f = models.CharField(null=False)
        self.assertRaises(ValidationError, f.clean, None, None)

    def test_datefield_cleans_date(self):
        f = models.DateField()
        self.assertEqual(datetime.date(2008, 10, 10), f.clean('2008-10-10', None))

    def test_boolean_field_doesnt_accept_empty_input(self):
        f = models.BooleanField()
        self.assertRaises(ValidationError, f.clean, None, None)


class BigIntegerFieldTests(django.test.TestCase):
    def test_limits(self):
        # Ensure that values that are right at the limits can be saved
        # and then retrieved without corruption.
        maxval = 9223372036854775807
        minval = -maxval - 1
        BigInt.objects.create(value=maxval)
        qs = BigInt.objects.filter(value__gte=maxval)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].value, maxval)
        BigInt.objects.create(value=minval)
        qs = BigInt.objects.filter(value__lte=minval)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].value, minval)

    def test_types(self):
        b = BigInt(value = 0)
        self.assertTrue(isinstance(b.value, (int, long)))
        b.save()
        self.assertTrue(isinstance(b.value, (int, long)))
        b = BigInt.objects.all()[0]
        self.assertTrue(isinstance(b.value, (int, long)))

    def test_coercing(self):
        BigInt.objects.create(value ='10')
        b = BigInt.objects.get(value = '10')
        self.assertEqual(b.value, 10)

class TypeCoercionTests(django.test.TestCase):
    """
    Test that database lookups can accept the wrong types and convert
    them with no error: especially on Postgres 8.3+ which does not do
    automatic casting at the DB level. See #10015.

    """
    def test_lookup_integer_in_charfield(self):
        self.assertEquals(Post.objects.filter(title=9).count(), 0)

    def test_lookup_integer_in_textfield(self):
        self.assertEquals(Post.objects.filter(body=24).count(), 0)

