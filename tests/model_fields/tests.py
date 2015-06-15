from __future__ import unicode_literals

import datetime
import unittest
from decimal import Decimal

from django import forms, test
from django.core import checks, validators
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, models, transaction
from django.db.models.fields import (
    NOT_PROVIDED, AutoField, BigIntegerField, BinaryField, BooleanField,
    CharField, CommaSeparatedIntegerField, DateField, DateTimeField,
    DecimalField, EmailField, FilePathField, FloatField, GenericIPAddressField,
    IntegerField, IPAddressField, NullBooleanField, PositiveIntegerField,
    PositiveSmallIntegerField, SlugField, SmallIntegerField, TextField,
    TimeField, URLField,
)
from django.db.models.fields.files import FileField, ImageField
from django.utils import six
from django.utils.functional import lazy

from .models import (
    Bar, BigD, BigIntegerModel, BigS, BooleanModel, DataModel, DateTimeModel,
    Document, FksToBooleans, FkToChar, FloatModel, Foo, GenericIPAddress,
    IntegerModel, NullBooleanModel, PositiveIntegerModel,
    PositiveSmallIntegerModel, Post, PrimaryKeyCharModel, RenamedField,
    SmallIntegerModel, VerboseNameField, Whiz, WhizIter, WhizIterEmpty,
)


class BasicFieldTests(test.TestCase):
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
        except ValidationError as e:
            self.fail("NullBooleanField failed validation with value of None: %s" % e.messages)

    def test_field_repr(self):
        """
        Regression test for #5931: __repr__ of a field also displays its name
        """
        f = Foo._meta.get_field('a')
        self.assertEqual(repr(f), '<django.db.models.fields.CharField: a>')
        f = models.fields.CharField()
        self.assertEqual(repr(f), '<django.db.models.fields.CharField>')

    def test_field_name(self):
        """
        Regression test for #14695: explicitly defined field name overwritten
        by model's attribute name.
        """
        instance = RenamedField()
        self.assertTrue(hasattr(instance, 'get_fieldname_display'))
        self.assertFalse(hasattr(instance, 'get_modelname_display'))

    def test_field_verbose_name(self):
        m = VerboseNameField
        for i in range(1, 25):
            self.assertEqual(m._meta.get_field('field%d' % i).verbose_name,
                             'verbose field%d' % i)

        self.assertEqual(m._meta.get_field('id').verbose_name, 'verbose pk')

    def test_float_validates_object(self):
        instance = FloatModel(size=2.5)
        # Try setting float field to unsaved object
        instance.size = instance
        with transaction.atomic():
            with self.assertRaises(TypeError):
                instance.save()
        # Set value to valid and save
        instance.size = 2.5
        instance.save()
        self.assertTrue(instance.id)
        # Set field to object on saved instance
        instance.size = instance
        with transaction.atomic():
            with self.assertRaises(TypeError):
                instance.save()
        # Try setting field to object on retrieved object
        obj = FloatModel.objects.get(pk=instance.id)
        obj.size = obj
        with self.assertRaises(TypeError):
            obj.save()

    def test_choices_form_class(self):
        """Can supply a custom choices form class. Regression for #20999."""
        choices = [('a', 'a')]
        field = models.CharField(choices=choices)
        klass = forms.TypedMultipleChoiceField
        self.assertIsInstance(field.formfield(choices_form_class=klass), klass)

    def test_field_str(self):
        from django.utils.encoding import force_str
        f = Foo._meta.get_field('a')
        self.assertEqual(force_str(f), "model_fields.Foo.a")


class DecimalFieldTests(test.TestCase):
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
        self.assertEqual(f._format(f.to_python(2)), '2.0')
        self.assertEqual(f._format(f.to_python('2.6')), '2.6')
        self.assertEqual(f._format(None), None)

    def test_get_db_prep_lookup(self):
        f = models.DecimalField(max_digits=5, decimal_places=1)
        self.assertEqual(f.get_db_prep_lookup('exact', None, connection=connection), [None])

    def test_filter_with_strings(self):
        """
        We should be able to filter decimal fields using strings (#8023)
        """
        Foo.objects.create(id=1, a='abc', d=Decimal("12.34"))
        self.assertEqual(list(Foo.objects.filter(d='1.23')), [])

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


class ForeignKeyTests(test.TestCase):
    def test_callable_default(self):
        """Test the use of a lazy callable for ForeignKey.default"""
        a = Foo.objects.create(id=1, a='abc', d=Decimal("12.34"))
        b = Bar.objects.create(b="bcd")
        self.assertEqual(b.a, a)

    @test.skipIfDBFeature('interprets_empty_strings_as_nulls')
    def test_empty_string_fk(self):
        """
        Test that foreign key values to empty strings don't get converted
        to None (#19299)
        """
        char_model_empty = PrimaryKeyCharModel.objects.create(string='')
        fk_model_empty = FkToChar.objects.create(out=char_model_empty)
        fk_model_empty = FkToChar.objects.select_related('out').get(id=fk_model_empty.pk)
        self.assertEqual(fk_model_empty.out, char_model_empty)

    def test_warning_when_unique_true_on_fk(self):
        class FKUniqueTrue(models.Model):
            fk_field = models.ForeignKey(Foo, unique=True)

        model = FKUniqueTrue()
        expected_warnings = [
            checks.Warning(
                'Setting unique=True on a ForeignKey has the same effect as using a OneToOneField.',
                hint='ForeignKey(unique=True) is usually better served by a OneToOneField.',
                obj=FKUniqueTrue.fk_field.field,
                id='fields.W342',
            )
        ]
        warnings = model.check()
        self.assertEqual(warnings, expected_warnings)

    def test_related_name_converted_to_text(self):
        rel_name = Bar._meta.get_field('a').rel.related_name
        self.assertIsInstance(rel_name, six.text_type)


class DateTimeFieldTests(test.TestCase):
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

    @test.skipUnlessDBFeature("supports_microsecond_precision")
    def test_datetimes_save_completely(self):
        dat = datetime.date(2014, 3, 12)
        datetim = datetime.datetime(2014, 3, 12, 21, 22, 23, 240000)
        tim = datetime.time(21, 22, 23, 240000)
        DateTimeModel.objects.create(d=dat, dt=datetim, t=tim)
        obj = DateTimeModel.objects.first()
        self.assertTrue(obj)
        self.assertEqual(obj.d, dat)
        self.assertEqual(obj.dt, datetim)
        self.assertEqual(obj.t, tim)


class BooleanFieldTests(test.TestCase):
    def _test_get_db_prep_lookup(self, f):
        self.assertEqual(f.get_db_prep_lookup('exact', True, connection=connection), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', '1', connection=connection), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', 1, connection=connection), [True])
        self.assertEqual(f.get_db_prep_lookup('exact', False, connection=connection), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', '0', connection=connection), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', 0, connection=connection), [False])
        self.assertEqual(f.get_db_prep_lookup('exact', None, connection=connection), [None])

    def _test_to_python(self, f):
        self.assertIs(f.to_python(1), True)
        self.assertIs(f.to_python(0), False)

    def test_booleanfield_get_db_prep_lookup(self):
        self._test_get_db_prep_lookup(models.BooleanField())

    def test_nullbooleanfield_get_db_prep_lookup(self):
        self._test_get_db_prep_lookup(models.NullBooleanField())

    def test_booleanfield_to_python(self):
        self._test_to_python(models.BooleanField())

    def test_nullbooleanfield_to_python(self):
        self._test_to_python(models.NullBooleanField())

    def test_charfield_textfield_max_length_passed_to_formfield(self):
        """
        Test that CharField and TextField pass their max_length attributes to
        form fields created using their .formfield() method (#22206).
        """
        cf1 = models.CharField()
        cf2 = models.CharField(max_length=1234)
        self.assertIsNone(cf1.formfield().max_length)
        self.assertEqual(1234, cf2.formfield().max_length)

        tf1 = models.TextField()
        tf2 = models.TextField(max_length=2345)
        self.assertIsNone(tf1.formfield().max_length)
        self.assertEqual(2345, tf2.formfield().max_length)

    def test_booleanfield_choices_blank(self):
        """
        Test that BooleanField with choices and defaults doesn't generate a
        formfield with the blank option (#9640, #10549).
        """
        choices = [(1, 'Si'), (2, 'No')]
        f = models.BooleanField(choices=choices, default=1, null=False)
        self.assertEqual(f.formfield().choices, choices)

    def test_return_type(self):
        b = BooleanModel()
        b.bfield = True
        b.save()
        b2 = BooleanModel.objects.get(pk=b.pk)
        self.assertIsInstance(b2.bfield, bool)
        self.assertEqual(b2.bfield, True)

        b3 = BooleanModel()
        b3.bfield = False
        b3.save()
        b4 = BooleanModel.objects.get(pk=b3.pk)
        self.assertIsInstance(b4.bfield, bool)
        self.assertEqual(b4.bfield, False)

        b = NullBooleanModel()
        b.nbfield = True
        b.save()
        b2 = NullBooleanModel.objects.get(pk=b.pk)
        self.assertIsInstance(b2.nbfield, bool)
        self.assertEqual(b2.nbfield, True)

        b3 = NullBooleanModel()
        b3.nbfield = False
        b3.save()
        b4 = NullBooleanModel.objects.get(pk=b3.pk)
        self.assertIsInstance(b4.nbfield, bool)
        self.assertEqual(b4.nbfield, False)

        # http://code.djangoproject.com/ticket/13293
        # Verify that when an extra clause exists, the boolean
        # conversions are applied with an offset
        b5 = BooleanModel.objects.all().extra(
            select={'string_col': 'string'})[0]
        self.assertNotIsInstance(b5.pk, bool)

    def test_select_related(self):
        """
        Test type of boolean fields when retrieved via select_related() (MySQL,
        #15040)
        """
        bmt = BooleanModel.objects.create(bfield=True)
        bmf = BooleanModel.objects.create(bfield=False)
        nbmt = NullBooleanModel.objects.create(nbfield=True)
        nbmf = NullBooleanModel.objects.create(nbfield=False)

        m1 = FksToBooleans.objects.create(bf=bmt, nbf=nbmt)
        m2 = FksToBooleans.objects.create(bf=bmf, nbf=nbmf)

        # Test select_related('fk_field_name')
        ma = FksToBooleans.objects.select_related('bf').get(pk=m1.id)
        # verify types -- shouldn't be 0/1
        self.assertIsInstance(ma.bf.bfield, bool)
        self.assertIsInstance(ma.nbf.nbfield, bool)
        # verify values
        self.assertEqual(ma.bf.bfield, True)
        self.assertEqual(ma.nbf.nbfield, True)

        # Test select_related()
        mb = FksToBooleans.objects.select_related().get(pk=m1.id)
        mc = FksToBooleans.objects.select_related().get(pk=m2.id)
        # verify types -- shouldn't be 0/1
        self.assertIsInstance(mb.bf.bfield, bool)
        self.assertIsInstance(mb.nbf.nbfield, bool)
        self.assertIsInstance(mc.bf.bfield, bool)
        self.assertIsInstance(mc.nbf.nbfield, bool)
        # verify values
        self.assertEqual(mb.bf.bfield, True)
        self.assertEqual(mb.nbf.nbfield, True)
        self.assertEqual(mc.bf.bfield, False)
        self.assertEqual(mc.nbf.nbfield, False)

    def test_null_default(self):
        """
        Check that a BooleanField defaults to None -- which isn't
        a valid value (#15124).
        """
        # Patch the boolean field's default value. We give it a default
        # value when defining the model to satisfy the check tests
        # #20895.
        boolean_field = BooleanModel._meta.get_field('bfield')
        self.assertTrue(boolean_field.has_default())
        old_default = boolean_field.default
        try:
            boolean_field.default = NOT_PROVIDED
            # check patch was successful
            self.assertFalse(boolean_field.has_default())
            b = BooleanModel()
            self.assertIsNone(b.bfield)
            with transaction.atomic():
                with self.assertRaises(IntegrityError):
                    b.save()
        finally:
            boolean_field.default = old_default

        nb = NullBooleanModel()
        self.assertIsNone(nb.nbfield)
        nb.save()           # no error


class ChoicesTests(test.TestCase):
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

    def test_iterator_choices(self):
        """
        Check that get_choices works with Iterators (#23112).
        """
        self.assertEqual(WhizIter(c=1).c, 1)          # A nested value
        self.assertEqual(WhizIter(c=9).c, 9)          # Invalid value
        self.assertEqual(WhizIter(c=None).c, None)    # Blank value
        self.assertEqual(WhizIter(c='').c, '')        # Empty value

    def test_empty_iterator_choices(self):
        """
        Check that get_choices works with empty iterators (#23112).
        """
        self.assertEqual(WhizIterEmpty(c="a").c, "a")      # A nested value
        self.assertEqual(WhizIterEmpty(c="b").c, "b")      # Invalid value
        self.assertEqual(WhizIterEmpty(c=None).c, None)    # Blank value
        self.assertEqual(WhizIterEmpty(c='').c, '')        # Empty value

    def test_charfield_get_choices_with_blank_iterator(self):
        """
        Check that get_choices works with an empty Iterator
        """
        f = models.CharField(choices=(x for x in []))
        self.assertEqual(f.get_choices(include_blank=True), [('', '---------')])


class SlugFieldTests(test.TestCase):
    def test_slugfield_max_length(self):
        """
        Make sure SlugField honors max_length (#9706)
        """
        bs = BigS.objects.create(s='slug' * 50)
        bs = BigS.objects.get(pk=bs.pk)
        self.assertEqual(bs.s, 'slug' * 50)


class ValidationTest(test.TestCase):
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
        f = models.CharField(max_length=1,
                             choices=[('a', 'A'), ('b', 'B')])
        self.assertEqual('a', f.clean('a', None))

    def test_charfield_with_choices_raises_error_on_invalid_choice(self):
        f = models.CharField(choices=[('a', 'A'), ('b', 'B')])
        self.assertRaises(ValidationError, f.clean, "not a", None)

    def test_charfield_get_choices_with_blank_defined(self):
        f = models.CharField(choices=[('', '<><>'), ('a', 'A')])
        self.assertEqual(f.get_choices(True), [('', '<><>'), ('a', 'A')])

    def test_charfield_get_choices_doesnt_evaluate_lazy_strings(self):
        # Regression test for #23098
        # Will raise ZeroDivisionError if lazy is evaluated
        lazy_func = lazy(lambda x: 0 / 0, int)
        f = models.CharField(choices=[(lazy_func('group'), (('a', 'A'), ('b', 'B')))])
        self.assertEqual(f.get_choices(True)[0], ('', '---------'))

    def test_choices_validation_supports_named_groups(self):
        f = models.IntegerField(
            choices=(('group', ((10, 'A'), (20, 'B'))), (30, 'C')))
        self.assertEqual(10, f.clean(10, None))

    def test_nullable_integerfield_raises_error_with_blank_false(self):
        f = models.IntegerField(null=True, blank=False)
        self.assertRaises(ValidationError, f.clean, None, None)

    def test_nullable_integerfield_cleans_none_on_null_and_blank_true(self):
        f = models.IntegerField(null=True, blank=True)
        self.assertIsNone(f.clean(None, None))

    def test_integerfield_raises_error_on_empty_input(self):
        f = models.IntegerField(null=False)
        self.assertRaises(ValidationError, f.clean, None, None)
        self.assertRaises(ValidationError, f.clean, '', None)

    def test_integerfield_validates_zero_against_choices(self):
        f = models.IntegerField(choices=((1, 1),))
        self.assertRaises(ValidationError, f.clean, '0', None)

    def test_charfield_raises_error_on_empty_input(self):
        f = models.CharField(null=False)
        self.assertRaises(ValidationError, f.clean, None, None)

    def test_datefield_cleans_date(self):
        f = models.DateField()
        self.assertEqual(datetime.date(2008, 10, 10), f.clean('2008-10-10', None))

    def test_boolean_field_doesnt_accept_empty_input(self):
        f = models.BooleanField()
        self.assertRaises(ValidationError, f.clean, None, None)


class IntegerFieldTests(test.TestCase):
    model = IntegerModel
    documented_range = (-2147483648, 2147483647)

    def test_documented_range(self):
        """
        Ensure that values within the documented safe range pass validation,
        can be saved and retrieved without corruption.
        """
        min_value, max_value = self.documented_range

        instance = self.model(value=min_value)
        instance.full_clean()
        instance.save()
        qs = self.model.objects.filter(value__lte=min_value)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].value, min_value)

        instance = self.model(value=max_value)
        instance.full_clean()
        instance.save()
        qs = self.model.objects.filter(value__gte=max_value)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs[0].value, max_value)

    def test_backend_range_validation(self):
        """
        Ensure that backend specific range are enforced at the model
        validation level. ref #12030.
        """
        field = self.model._meta.get_field('value')
        internal_type = field.get_internal_type()
        min_value, max_value = connection.ops.integer_field_range(internal_type)

        if min_value is not None:
            instance = self.model(value=min_value - 1)
            expected_message = validators.MinValueValidator.message % {
                'limit_value': min_value
            }
            with self.assertRaisesMessage(ValidationError, expected_message):
                instance.full_clean()
            instance.value = min_value
            instance.full_clean()

        if max_value is not None:
            instance = self.model(value=max_value + 1)
            expected_message = validators.MaxValueValidator.message % {
                'limit_value': max_value
            }
            with self.assertRaisesMessage(ValidationError, expected_message):
                instance.full_clean()
            instance.value = max_value
            instance.full_clean()

    def test_types(self):
        instance = self.model(value=0)
        self.assertIsInstance(instance.value, six.integer_types)
        instance.save()
        self.assertIsInstance(instance.value, six.integer_types)
        instance = self.model.objects.get()
        self.assertIsInstance(instance.value, six.integer_types)

    def test_coercing(self):
        self.model.objects.create(value='10')
        instance = self.model.objects.get(value='10')
        self.assertEqual(instance.value, 10)


class SmallIntegerFieldTests(IntegerFieldTests):
    model = SmallIntegerModel
    documented_range = (-32768, 32767)


class BigIntegerFieldTests(IntegerFieldTests):
    model = BigIntegerModel
    documented_range = (-9223372036854775808, 9223372036854775807)


class PositiveSmallIntegerFieldTests(IntegerFieldTests):
    model = PositiveSmallIntegerModel
    documented_range = (0, 32767)


class PositiveIntegerFieldTests(IntegerFieldTests):
    model = PositiveIntegerModel
    documented_range = (0, 2147483647)


class TypeCoercionTests(test.TestCase):
    """
    Test that database lookups can accept the wrong types and convert
    them with no error: especially on Postgres 8.3+ which does not do
    automatic casting at the DB level. See #10015.

    """
    def test_lookup_integer_in_charfield(self):
        self.assertEqual(Post.objects.filter(title=9).count(), 0)

    def test_lookup_integer_in_textfield(self):
        self.assertEqual(Post.objects.filter(body=24).count(), 0)


class FileFieldTests(unittest.TestCase):
    def test_clearable(self):
        """
        Test that FileField.save_form_data will clear its instance attribute
        value if passed False.

        """
        d = Document(myfile='something.txt')
        self.assertEqual(d.myfile, 'something.txt')
        field = d._meta.get_field('myfile')
        field.save_form_data(d, False)
        self.assertEqual(d.myfile, '')

    def test_unchanged(self):
        """
        Test that FileField.save_form_data considers None to mean "no change"
        rather than "clear".

        """
        d = Document(myfile='something.txt')
        self.assertEqual(d.myfile, 'something.txt')
        field = d._meta.get_field('myfile')
        field.save_form_data(d, None)
        self.assertEqual(d.myfile, 'something.txt')

    def test_changed(self):
        """
        Test that FileField.save_form_data, if passed a truthy value, updates
        its instance attribute.

        """
        d = Document(myfile='something.txt')
        self.assertEqual(d.myfile, 'something.txt')
        field = d._meta.get_field('myfile')
        field.save_form_data(d, 'else.txt')
        self.assertEqual(d.myfile, 'else.txt')

    def test_delete_when_file_unset(self):
        """
        Calling delete on an unset FileField should not call the file deletion
        process, but fail silently (#20660).
        """
        d = Document()
        try:
            d.myfile.delete()
        except OSError:
            self.fail("Deleting an unset FileField should not raise OSError.")


class BinaryFieldTests(test.TestCase):
    binary_data = b'\x00\x46\xFE'

    def test_set_and_retrieve(self):
        data_set = (self.binary_data, six.memoryview(self.binary_data))
        for bdata in data_set:
            dm = DataModel(data=bdata)
            dm.save()
            dm = DataModel.objects.get(pk=dm.pk)
            self.assertEqual(bytes(dm.data), bytes(bdata))
            # Resave (=update)
            dm.save()
            dm = DataModel.objects.get(pk=dm.pk)
            self.assertEqual(bytes(dm.data), bytes(bdata))
            # Test default value
            self.assertEqual(bytes(dm.short_data), b'\x08')

    def test_max_length(self):
        dm = DataModel(short_data=self.binary_data * 4)
        self.assertRaises(ValidationError, dm.full_clean)


class GenericIPAddressFieldTests(test.TestCase):
    def test_genericipaddressfield_formfield_protocol(self):
        """
        Test that GenericIPAddressField with a specified protocol does not
        generate a formfield with no specified protocol. See #20740.
        """
        model_field = models.GenericIPAddressField(protocol='IPv4')
        form_field = model_field.formfield()
        self.assertRaises(ValidationError, form_field.clean, '::1')
        model_field = models.GenericIPAddressField(protocol='IPv6')
        form_field = model_field.formfield()
        self.assertRaises(ValidationError, form_field.clean, '127.0.0.1')

    def test_null_value(self):
        """
        Null values should be resolved to None in Python (#24078).
        """
        GenericIPAddress.objects.create()
        o = GenericIPAddress.objects.get()
        self.assertIsNone(o.ip)

    def test_save_load(self):
        instance = GenericIPAddress.objects.create(ip='::1')
        loaded = GenericIPAddress.objects.get()
        self.assertEqual(loaded.ip, instance.ip)


class PromiseTest(test.TestCase):
    def test_AutoField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(
            AutoField(primary_key=True).get_prep_value(lazy_func()),
            int)

    @unittest.skipIf(six.PY3, "Python 3 has no `long` type.")
    def test_BigIntegerField(self):
        # NOQA: long undefined on PY3
        lazy_func = lazy(lambda: long(9999999999999999999), long)  # NOQA
        self.assertIsInstance(
            BigIntegerField().get_prep_value(lazy_func()),
            long)  # NOQA

    def test_BinaryField(self):
        lazy_func = lazy(lambda: b'', bytes)
        self.assertIsInstance(
            BinaryField().get_prep_value(lazy_func()),
            bytes)

    def test_BooleanField(self):
        lazy_func = lazy(lambda: True, bool)
        self.assertIsInstance(
            BooleanField().get_prep_value(lazy_func()),
            bool)

    def test_CharField(self):
        lazy_func = lazy(lambda: '', six.text_type)
        self.assertIsInstance(
            CharField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            CharField().get_prep_value(lazy_func()),
            six.text_type)

    def test_CommaSeparatedIntegerField(self):
        lazy_func = lazy(lambda: '1,2', six.text_type)
        self.assertIsInstance(
            CommaSeparatedIntegerField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            CommaSeparatedIntegerField().get_prep_value(lazy_func()),
            six.text_type)

    def test_DateField(self):
        lazy_func = lazy(lambda: datetime.date.today(), datetime.date)
        self.assertIsInstance(
            DateField().get_prep_value(lazy_func()),
            datetime.date)

    def test_DateTimeField(self):
        lazy_func = lazy(lambda: datetime.datetime.now(), datetime.datetime)
        self.assertIsInstance(
            DateTimeField().get_prep_value(lazy_func()),
            datetime.datetime)

    def test_DecimalField(self):
        lazy_func = lazy(lambda: Decimal('1.2'), Decimal)
        self.assertIsInstance(
            DecimalField().get_prep_value(lazy_func()),
            Decimal)

    def test_EmailField(self):
        lazy_func = lazy(lambda: 'mailbox@domain.com', six.text_type)
        self.assertIsInstance(
            EmailField().get_prep_value(lazy_func()),
            six.text_type)

    def test_FileField(self):
        lazy_func = lazy(lambda: 'filename.ext', six.text_type)
        self.assertIsInstance(
            FileField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            FileField().get_prep_value(lazy_func()),
            six.text_type)

    def test_FilePathField(self):
        lazy_func = lazy(lambda: 'tests.py', six.text_type)
        self.assertIsInstance(
            FilePathField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            FilePathField().get_prep_value(lazy_func()),
            six.text_type)

    def test_FloatField(self):
        lazy_func = lazy(lambda: 1.2, float)
        self.assertIsInstance(
            FloatField().get_prep_value(lazy_func()),
            float)

    def test_ImageField(self):
        lazy_func = lazy(lambda: 'filename.ext', six.text_type)
        self.assertIsInstance(
            ImageField().get_prep_value(lazy_func()),
            six.text_type)

    def test_IntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(
            IntegerField().get_prep_value(lazy_func()),
            int)

    def test_IPAddressField(self):
        lazy_func = lazy(lambda: '127.0.0.1', six.text_type)
        self.assertIsInstance(
            IPAddressField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            IPAddressField().get_prep_value(lazy_func()),
            six.text_type)

    def test_IPAddressField_deprecated(self):
        class IPAddressModel(models.Model):
            ip = IPAddressField()

        model = IPAddressModel()
        self.assertEqual(
            model.check(),
            [checks.Warning(
                'IPAddressField has been deprecated. Support for it '
                '(except in historical migrations) will be removed in Django 1.9.',
                hint='Use GenericIPAddressField instead.',
                obj=IPAddressModel._meta.get_field('ip'),
                id='fields.W900',
            )],
        )

    def test_GenericIPAddressField(self):
        lazy_func = lazy(lambda: '127.0.0.1', six.text_type)
        self.assertIsInstance(
            GenericIPAddressField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            GenericIPAddressField().get_prep_value(lazy_func()),
            six.text_type)

    def test_NullBooleanField(self):
        lazy_func = lazy(lambda: True, bool)
        self.assertIsInstance(
            NullBooleanField().get_prep_value(lazy_func()),
            bool)

    def test_PositiveIntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(
            PositiveIntegerField().get_prep_value(lazy_func()),
            int)

    def test_PositiveSmallIntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(
            PositiveSmallIntegerField().get_prep_value(lazy_func()),
            int)

    def test_SlugField(self):
        lazy_func = lazy(lambda: 'slug', six.text_type)
        self.assertIsInstance(
            SlugField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            SlugField().get_prep_value(lazy_func()),
            six.text_type)

    def test_SmallIntegerField(self):
        lazy_func = lazy(lambda: 1, int)
        self.assertIsInstance(
            SmallIntegerField().get_prep_value(lazy_func()),
            int)

    def test_TextField(self):
        lazy_func = lazy(lambda: 'Abc', six.text_type)
        self.assertIsInstance(
            TextField().get_prep_value(lazy_func()),
            six.text_type)
        lazy_func = lazy(lambda: 0, int)
        self.assertIsInstance(
            TextField().get_prep_value(lazy_func()),
            six.text_type)

    def test_TimeField(self):
        lazy_func = lazy(lambda: datetime.datetime.now().time(), datetime.time)
        self.assertIsInstance(
            TimeField().get_prep_value(lazy_func()),
            datetime.time)

    def test_URLField(self):
        lazy_func = lazy(lambda: 'http://domain.com', six.text_type)
        self.assertIsInstance(
            URLField().get_prep_value(lazy_func()),
            six.text_type)


class CustomFieldTests(unittest.TestCase):

    def test_14786(self):
        """
        Regression test for #14786 -- Test that field values are not prepared
        twice in get_db_prep_lookup().
        """
        class NoopField(models.TextField):
            def __init__(self, *args, **kwargs):
                self.prep_value_count = 0
                super(NoopField, self).__init__(*args, **kwargs)

            def get_prep_value(self, value):
                self.prep_value_count += 1
                return super(NoopField, self).get_prep_value(value)

        field = NoopField()
        field.get_db_prep_lookup(
            'exact', 'TEST', connection=connection, prepared=False
        )
        self.assertEqual(field.prep_value_count, 1)
