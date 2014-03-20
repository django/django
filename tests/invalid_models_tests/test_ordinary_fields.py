# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from django.core.checks import Error
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, models

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


class CharFieldTests(IsolatedModelsTestCase):

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
            import django.utils.image  # NOQA
        except ImproperlyConfigured:
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
                      'or run command "pip install pillow".'),
                obj=field,
                id='fields.E210',
            ),
        ]
        self.assertEqual(errors, expected)
