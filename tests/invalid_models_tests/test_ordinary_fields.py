# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from django.core.checks import Error, Warning as DjangoWarning
from django.db import connection, models
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from .base import IsolatedModelsTestCase


class AutoFieldTests(IsolatedModelsTestCase):

    def test_valid_case(self):
        class Model(models.Model):
            id = models.AutoField(primary_key=True)

        field = Model._meta.get_field('id')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)

    def test_primary_key(self):
        # primary_key must be True. Refs #12467.
        class Model(models.Model):
            field = models.AutoField(primary_key=False)

            # Prevent Django from autocreating `id` AutoField, which would
            # result in an error, because a model must have exactly one
            # AutoField.
            another = models.IntegerField(primary_key=True)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                'AutoFields must set primary_key=True.',
                hint=None,
                obj=field,
                id='fields.E100',
            ),
        ]
        self.assertEqual(errors, expected)


class BooleanFieldTests(IsolatedModelsTestCase):

    def test_nullable_boolean_field(self):
        class Model(models.Model):
            field = models.BooleanField(null=True)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                'BooleanFields do not accept null values.',
                hint='Use a NullBooleanField instead.',
                obj=field,
                id='fields.E110',
            ),
        ]
        self.assertEqual(errors, expected)


class CharFieldTests(IsolatedModelsTestCase, TestCase):

    def test_valid_field(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=255,
                choices=[
                    ('1', 'item1'),
                    ('2', 'item2'),
                ],
                db_index=True)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)

    def test_missing_max_length(self):
        class Model(models.Model):
            field = models.CharField()

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "CharFields must define a 'max_length' attribute.",
                hint=None,
                obj=field,
                id='fields.E120',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_negative_max_length(self):
        class Model(models.Model):
            field = models.CharField(max_length=-1)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'max_length' must be a positive integer.",
                hint=None,
                obj=field,
                id='fields.E121',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_bad_max_length_value(self):
        class Model(models.Model):
            field = models.CharField(max_length="bad")

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'max_length' must be a positive integer.",
                hint=None,
                obj=field,
                id='fields.E121',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_str_max_length_value(self):
        class Model(models.Model):
            field = models.CharField(max_length='20')

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'max_length' must be a positive integer.",
                hint=None,
                obj=field,
                id='fields.E121',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_non_iterable_choices(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices='bad')

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'choices' must be an iterable (e.g., a list or tuple).",
                hint=None,
                obj=field,
                id='fields.E004',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_choices_containing_non_pairs(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=[(1, 2, 3), (1, 2, 3)])

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'choices' must be an iterable containing (actual value, human readable name) tuples.",
                hint=None,
                obj=field,
                id='fields.E005',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_bad_db_index_value(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, db_index='bad')

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'db_index' must be None, True or False.",
                hint=None,
                obj=field,
                id='fields.E006',
            ),
        ]
        self.assertEqual(errors, expected)

    @unittest.skipUnless(connection.vendor == 'mysql',
                         "Test valid only for MySQL")
    def test_too_long_char_field_under_mysql(self):
        from django.db.backends.mysql.validation import DatabaseValidation

        class Model(models.Model):
            field = models.CharField(unique=True, max_length=256)

        field = Model._meta.get_field('field')
        validator = DatabaseValidation(connection=None)
        errors = validator.check_field(field)
        expected = [
            Error(
                'MySQL does not allow unique CharFields to have a max_length > 255.',
                hint=None,
                obj=field,
                id='mysql.E001',
            )
        ]
        self.assertEqual(errors, expected)


class DateFieldTests(IsolatedModelsTestCase, TestCase):

    def test_auto_now_and_auto_now_add_raise_error(self):
        class Model(models.Model):
            field0 = models.DateTimeField(auto_now=True, auto_now_add=True, default=now)
            field1 = models.DateTimeField(auto_now=True, auto_now_add=False, default=now)
            field2 = models.DateTimeField(auto_now=False, auto_now_add=True, default=now)
            field3 = models.DateTimeField(auto_now=True, auto_now_add=True, default=None)

        expected = []
        checks = []
        for i in range(4):
            field = Model._meta.get_field('field%d' % i)
            expected.append(Error(
                "The options auto_now, auto_now_add, and default "
                "are mutually exclusive. Only one of these options "
                "may be present.",
                hint=None,
                obj=field,
                id='fields.E160',
            ))
            checks.extend(field.check())
            self.assertEqual(checks, expected)

    def test_fix_default_value(self):
        class Model(models.Model):
            field_dt = models.DateField(default=now())
            field_d = models.DateField(default=now().date())
            field_now = models.DateField(default=now)

        field_dt = Model._meta.get_field('field_dt')
        field_d = Model._meta.get_field('field_d')
        field_now = Model._meta.get_field('field_now')
        errors = field_dt.check()
        errors.extend(field_d.check())
        errors.extend(field_now.check())  # doesn't raise a warning
        expected = [
            DjangoWarning(
                'Fixed default value provided.',
                hint='It seems you set a fixed date / time / datetime '
                     'value as default for this field. This may not be '
                     'what you want. If you want to have the current date '
                     'as default, use `django.utils.timezone.now`',
                obj=field_dt,
                id='fields.W161',
            ),
            DjangoWarning(
                'Fixed default value provided.',
                hint='It seems you set a fixed date / time / datetime '
                     'value as default for this field. This may not be '
                     'what you want. If you want to have the current date '
                     'as default, use `django.utils.timezone.now`',
                obj=field_d,
                id='fields.W161',
            )
        ]
        maxDiff = self.maxDiff
        self.maxDiff = None
        self.assertEqual(errors, expected)
        self.maxDiff = maxDiff

    @override_settings(USE_TZ=True)
    def test_fix_default_value_tz(self):
        self.test_fix_default_value()


class DateTimeFieldTests(IsolatedModelsTestCase, TestCase):

    def test_fix_default_value(self):
        class Model(models.Model):
            field_dt = models.DateTimeField(default=now())
            field_d = models.DateTimeField(default=now().date())
            field_now = models.DateTimeField(default=now)

        field_dt = Model._meta.get_field('field_dt')
        field_d = Model._meta.get_field('field_d')
        field_now = Model._meta.get_field('field_now')
        errors = field_dt.check()
        errors.extend(field_d.check())
        errors.extend(field_now.check())  # doesn't raise a warning
        expected = [
            DjangoWarning(
                'Fixed default value provided.',
                hint='It seems you set a fixed date / time / datetime '
                     'value as default for this field. This may not be '
                     'what you want. If you want to have the current date '
                     'as default, use `django.utils.timezone.now`',
                obj=field_dt,
                id='fields.W161',
            ),
            DjangoWarning(
                'Fixed default value provided.',
                hint='It seems you set a fixed date / time / datetime '
                     'value as default for this field. This may not be '
                     'what you want. If you want to have the current date '
                     'as default, use `django.utils.timezone.now`',
                obj=field_d,
                id='fields.W161',
            )
        ]
        maxDiff = self.maxDiff
        self.maxDiff = None
        self.assertEqual(errors, expected)
        self.maxDiff = maxDiff

    @override_settings(USE_TZ=True)
    def test_fix_default_value_tz(self):
        self.test_fix_default_value()


class DecimalFieldTests(IsolatedModelsTestCase):

    def test_required_attributes(self):
        class Model(models.Model):
            field = models.DecimalField()

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "DecimalFields must define a 'decimal_places' attribute.",
                hint=None,
                obj=field,
                id='fields.E130',
            ),
            Error(
                "DecimalFields must define a 'max_digits' attribute.",
                hint=None,
                obj=field,
                id='fields.E132',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_negative_max_digits_and_decimal_places(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits=-1, decimal_places=-1)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'decimal_places' must be a non-negative integer.",
                hint=None,
                obj=field,
                id='fields.E131',
            ),
            Error(
                "'max_digits' must be a positive integer.",
                hint=None,
                obj=field,
                id='fields.E133',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_bad_values_of_max_digits_and_decimal_places(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits="bad", decimal_places="bad")

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'decimal_places' must be a non-negative integer.",
                hint=None,
                obj=field,
                id='fields.E131',
            ),
            Error(
                "'max_digits' must be a positive integer.",
                hint=None,
                obj=field,
                id='fields.E133',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_decimal_places_greater_than_max_digits(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits=9, decimal_places=10)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'max_digits' must be greater or equal to 'decimal_places'.",
                hint=None,
                obj=field,
                id='fields.E134',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_valid_field(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits=10, decimal_places=10)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)


class FileFieldTests(IsolatedModelsTestCase):

    def test_valid_case(self):
        class Model(models.Model):
            field = models.FileField(upload_to='somewhere')

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)

    def test_unique(self):
        class Model(models.Model):
            field = models.FileField(unique=False, upload_to='somewhere')

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'unique' is not a valid argument for a FileField.",
                hint=None,
                obj=field,
                id='fields.E200',
            )
        ]
        self.assertEqual(errors, expected)

    def test_primary_key(self):
        class Model(models.Model):
            field = models.FileField(primary_key=False, upload_to='somewhere')

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "'primary_key' is not a valid argument for a FileField.",
                hint=None,
                obj=field,
                id='fields.E201',
            )
        ]
        self.assertEqual(errors, expected)


class FilePathFieldTests(IsolatedModelsTestCase):

    def test_forbidden_files_and_folders(self):
        class Model(models.Model):
            field = models.FilePathField(allow_files=False, allow_folders=False)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                "FilePathFields must have either 'allow_files' or 'allow_folders' set to True.",
                hint=None,
                obj=field,
                id='fields.E140',
            ),
        ]
        self.assertEqual(errors, expected)


class GenericIPAddressFieldTests(IsolatedModelsTestCase):

    def test_non_nullable_blank(self):
        class Model(models.Model):
            field = models.GenericIPAddressField(null=False, blank=True)

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [
            Error(
                ('GenericIPAddressFields cannot have blank=True if null=False, '
                 'as blank values are stored as nulls.'),
                hint=None,
                obj=field,
                id='fields.E150',
            ),
        ]
        self.assertEqual(errors, expected)


class ImageFieldTests(IsolatedModelsTestCase):

    def test_pillow_installed(self):
        try:
            from PIL import Image  # NOQA
        except ImportError:
            pillow_installed = False
        else:
            pillow_installed = True

        class Model(models.Model):
            field = models.ImageField(upload_to='somewhere')

        field = Model._meta.get_field('field')
        errors = field.check()
        expected = [] if pillow_installed else [
            Error(
                'Cannot use ImageField because Pillow is not installed.',
                hint=('Get Pillow at https://pypi.python.org/pypi/Pillow '
                      'or run command "pip install Pillow".'),
                obj=field,
                id='fields.E210',
            ),
        ]
        self.assertEqual(errors, expected)


class IntegerFieldTests(IsolatedModelsTestCase):

    def test_max_length_warning(self):
        class Model(models.Model):
            value = models.IntegerField(max_length=2)

        value = Model._meta.get_field('value')
        errors = Model.check()
        expected = [
            DjangoWarning(
                "'max_length' is ignored when used with IntegerField",
                hint="Remove 'max_length' from field",
                obj=value,
                id='fields.W122',
            )
        ]
        self.assertEqual(errors, expected)


class TimeFieldTests(IsolatedModelsTestCase, TestCase):

    def test_fix_default_value(self):
        class Model(models.Model):
            field_dt = models.TimeField(default=now())
            field_t = models.TimeField(default=now().time())
            field_now = models.DateField(default=now)

        field_dt = Model._meta.get_field('field_dt')
        field_t = Model._meta.get_field('field_t')
        field_now = Model._meta.get_field('field_now')
        errors = field_dt.check()
        errors.extend(field_t.check())
        errors.extend(field_now.check())  # doesn't raise a warning
        expected = [
            DjangoWarning(
                'Fixed default value provided.',
                hint='It seems you set a fixed date / time / datetime '
                     'value as default for this field. This may not be '
                     'what you want. If you want to have the current date '
                     'as default, use `django.utils.timezone.now`',
                obj=field_dt,
                id='fields.W161',
            ),
            DjangoWarning(
                'Fixed default value provided.',
                hint='It seems you set a fixed date / time / datetime '
                     'value as default for this field. This may not be '
                     'what you want. If you want to have the current date '
                     'as default, use `django.utils.timezone.now`',
                obj=field_t,
                id='fields.W161',
            )
        ]
        maxDiff = self.maxDiff
        self.maxDiff = None
        self.assertEqual(errors, expected)
        self.maxDiff = maxDiff

    @override_settings(USE_TZ=True)
    def test_fix_default_value_tz(self):
        self.test_fix_default_value()
