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
                index_together = [('a', 'b'), 42]

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

    def test_non_list(self):
        class Model(models.Model):
            class Meta:
                unique_together = 'not-a-list'

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


class FieldNamesTests(IsolatedModelsTestCase):

    def test_ending_with_underscore(self):
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

    def test_including_separator(self):
        class Model(models.Model):
            some__field = models.IntegerField()

        errors = Model.check()
        expected = [
            Error(
                'Field names must not contain "__".',
                hint=None,
                obj=Model._meta.get_field('some__field'),
                id='E052',
            )
        ]
        self.assertEqual(errors, expected)

    def test_pk(self):
        class Model(models.Model):
            pk = models.IntegerField()

        errors = Model.check()
        expected = [
            Error(
                'Cannot use "pk" as a field name since it is a reserved name.',
                hint=None,
                obj=Model._meta.get_field('pk'),
                id='E051',
            )
        ]
        self.assertEqual(errors, expected)


class ShadowingFieldsTests(IsolatedModelsTestCase):

    def test_multiinheritance_clash(self):
        class Mother(models.Model):
            clash = models.IntegerField()

        class Father(models.Model):
            clash = models.IntegerField()

        class Child(Mother, Father):
            # Here we have two clashed: id (automatic field) and clash, because
            # both parents define these fields.
            pass

        errors = Child.check()
        expected = [
            Error(
                ('The field "id" from parent model '
                 'invalid_models_tests.mother clashes with the field "id" '
                 'from parent model invalid_models_tests.father.'),
                hint=None,
                obj=Child,
                id='E053',
            ),
            Error(
                ('The field "clash" from parent model '
                 'invalid_models_tests.mother clashes with the field "clash" '
                 'from parent model invalid_models_tests.father.'),
                hint=None,
                obj=Child,
                id='E053',
            )
        ]
        self.assertEqual(errors, expected)

    def test_inheritance_clash(self):
        class Parent(models.Model):
            f_id = models.IntegerField()

        class Target(models.Model):
            # This field doesn't result in a clash.
            f_id = models.IntegerField()

        class Child(Parent):
            # This field clashes with parent "f_id" field.
            f = models.ForeignKey(Target)

        errors = Child.check()
        expected = [
            Error(
                ('The field clashes with the field "f_id" '
                 'from model invalid_models_tests.parent.'),
                hint=None,
                obj=Child._meta.get_field('f'),
                id='E054',
            )
        ]
        self.assertEqual(errors, expected)

    def test_id_clash(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk = models.ForeignKey(Target)
            fk_id = models.IntegerField()

        errors = Model.check()
        expected = [
            Error(
                ('The field clashes with the field "fk" from model '
                 'invalid_models_tests.model.'),
                hint=None,
                obj=Model._meta.get_field('fk_id'),
                id='E054',
            )
        ]
        self.assertEqual(errors, expected)


class OtherModelTests(IsolatedModelsTestCase):

    def test_unique_primary_key(self):
        invalid_id = models.IntegerField(primary_key=False)

        class Model(models.Model):
            id = invalid_id

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
