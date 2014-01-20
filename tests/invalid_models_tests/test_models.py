# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.core.checks import Error
from django.db import models
from django.test.utils import override_settings

from .base import IsolatedModelsTestCase


class IndexTogetherTests(IsolatedModelsTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = 42

        errors = Model.check()
        expected = [
            Error(
                '"index_together" must be a list or tuple.',
                hint=None,
                obj=Model,
                id='E006',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_non_list(self):
        class Model(models.Model):
            class Meta:
                index_together = 'not-a-list'

        errors = Model.check()
        expected = [
            Error(
                '"index_together" must be a list or tuple.',
                hint=None,
                obj=Model,
                id='E006',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_list_containing_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = [
                    'non-iterable',
                    'second-non-iterable',
                ]

        errors = Model.check()
        expected = [
            Error(
                'All "index_together" elements must be lists or tuples.',
                hint=None,
                obj=Model,
                id='E007',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                index_together = [
                    ["missing_field"],
                ]

        errors = Model.check()
        expected = [
            Error(
                '"index_together" points to a missing field named "missing_field".',
                hint='Ensure that you did not misspell the field name.',
                obj=Model,
                id='E010',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                index_together = [
                    ["m2m"],
                ]

        errors = Model.check()
        expected = [
            Error(
                ('"index_together" refers to a m2m "m2m" field, but '
                 'ManyToManyFields are not supported in "index_together".'),
                hint=None,
                obj=Model,
                id='E011',
            ),
        ]
        self.assertEqual(errors, expected)


# unique_together tests are very similar to index_together tests.
class UniqueTogetherTests(IsolatedModelsTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                unique_together = 42

        errors = Model.check()
        expected = [
            Error(
                '"unique_together" must be a list or tuple.',
                hint=None,
                obj=Model,
                id='E008',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_list_containing_non_iterable(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                unique_together = [('a', 'b'), 42]

        errors = Model.check()
        expected = [
            Error(
                'All "unique_together" elements must be lists or tuples.',
                hint=None,
                obj=Model,
                id='E009',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_valid_model(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                # unique_together can be a simple tuple
                unique_together = ('one', 'two')

        errors = Model.check()
        self.assertEqual(errors, [])

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                unique_together = [
                    ["missing_field"],
                ]

        errors = Model.check()
        expected = [
            Error(
                '"unique_together" points to a missing field named "missing_field".',
                hint='Ensure that you did not misspell the field name.',
                obj=Model,
                id='E010',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_pointing_to_m2m(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                unique_together = [
                    ["m2m"],
                ]

        errors = Model.check()
        expected = [
            Error(
                ('"unique_together" refers to a m2m "m2m" field, but '
                 'ManyToManyFields are not supported in "unique_together".'),
                hint=None,
                obj=Model,
                id='E011',
            ),
        ]
        self.assertEqual(errors, expected)


class OtherModelTests(IsolatedModelsTestCase):

    def test_unique_primary_key(self):
        class Model(models.Model):
            id = models.IntegerField(primary_key=False)

        errors = Model.check()
        expected = [
            Error(
                ('You cannot use "id" as a field name, because each model '
                 'automatically gets an "id" field if none of the fields '
                 'have primary_key=True.'),
                hint='Remove or rename "id" field or add primary_key=True to a field.',
                obj=Model,
                id='E005',
            ),
            Error(
                'Field "id" has column name "id" that is already used.',
                hint=None,
                obj=Model,
            )
        ]
        self.assertEqual(errors, expected)

    def test_field_names_ending_with_underscore(self):
        class Model(models.Model):
            field_ = models.CharField(max_length=10)
            m2m_ = models.ManyToManyField('self')

        errors = Model.check()
        expected = [
            Error(
                'Field names must not end with underscores.',
                hint=None,
                obj=Model._meta.get_field('field_'),
                id='E001',
            ),
            Error(
                'Field names must not end with underscores.',
                hint=None,
                obj=Model._meta.get_field('m2m_'),
                id='E001',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_ordering_non_iterable(self):
        class Model(models.Model):
            class Meta:
                ordering = "missing_field"

        errors = Model.check()
        expected = [
            Error(
                ('"ordering" must be a tuple or list '
                 '(even if you want to order by only one field).'),
                hint=None,
                obj=Model,
                id='E012',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_ordering_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                ordering = ("missing_field",)

        errors = Model.check()
        expected = [
            Error(
                '"ordering" pointing to a missing "missing_field" field.',
                hint='Ensure that you did not misspell the field name.',
                obj=Model,
                id='E013',
            )
        ]
        self.assertEqual(errors, expected)

    @override_settings(TEST_SWAPPED_MODEL_BAD_VALUE='not-a-model')
    def test_swappable_missing_app_name(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_VALUE'

        errors = Model.check()
        expected = [
            Error(
                '"TEST_SWAPPED_MODEL_BAD_VALUE" is not of the form "app_label.app_name".',
                hint=None,
                obj=Model,
                id='E002',
            ),
        ]
        self.assertEqual(errors, expected)

    @override_settings(TEST_SWAPPED_MODEL_BAD_MODEL='not_an_app.Target')
    def test_swappable_missing_app(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_MODEL'

        errors = Model.check()
        expected = [
            Error(
                ('The model has been swapped out for not_an_app.Target '
                 'which has not been installed or is abstract.'),
                hint=('Ensure that you did not misspell the model name and '
                      'the app name as well as the model is not abstract. Does '
                      'your INSTALLED_APPS setting contain the "not_an_app" app?'),
                obj=Model,
                id='E003',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_two_m2m_through_same_relationship(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            primary = models.ManyToManyField(Person,
                through="Membership", related_name="primary")
            secondary = models.ManyToManyField(Person, through="Membership",
                related_name="secondary")

        class Membership(models.Model):
            person = models.ForeignKey(Person)
            group = models.ForeignKey(Group)

        errors = Group.check()
        expected = [
            Error(
                ('The model has two many-to-many relations through '
                 'the intermediary Membership model, which is not permitted.'),
                hint=None,
                obj=Group,
                id='E004',
            )
        ]
        self.assertEqual(errors, expected)
