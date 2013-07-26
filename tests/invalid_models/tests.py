from __future__ import unicode_literals

from types import MethodType

from django.core.checks import Error
from django.db import connection, models
from django.db.models.loading import cache
from django.test import TestCase
from django.test.utils import override_settings


class IsolatedModelsTestCase(TestCase):

    def setUp(self):
        # If you create a model in a test, the model is accessible in other
        # tests. To avoid this, we need to clear list of all models created in
        # `invalid_models` module.
        cache.app_models['invalid_models'] = {}
        cache._get_models_cache = {}

    tearDown = setUp


class CharFieldTests(TestCase):

    def test_valid_field(self):
        choices = [
            ('1', 'item1'),
            ('2', 'item2'),
        ]
        field = models.CharField(max_length=255, choices=choices, db_index=True)
        errors = field.check()
        self.assertEqual(errors, [])

    def test_missing_max_length_argument(self):
        field = models.CharField()
        errors = field.check()
        self.assertEqual(errors, [
            Error('No "max_length" argument.\n'
                'CharFields require "max_length" argument that is '
                'the maximum length (in characters) of the field.',
                hint=None, obj=field),
        ])

    def test_negative_max_length(self):
        field = models.CharField(max_length=-1)
        errors = field.check()
        self.assertEqual(errors, [
            Error('Invalid "max_length" value.\n'
                'CharFields require a "max_length" attribute that is '
                'the maximum length (in characters) of the field '
                'and is a positive integer.',
                hint=None, obj=field),
        ])

    def test_bad_value_of_max_length(self):
        field = models.CharField(max_length="bad")
        errors = field.check()
        self.assertEqual(errors, [
            Error('Invalid "max_length" value.\n'
                'CharFields require a "max_length" attribute that is '
                'the maximum length (in characters) of the field '
                'and is a positive integer.',
                hint=None, obj=field),
        ])

    def test_non_iterable_choices(self):
        field = models.CharField(max_length=10, choices='bad')
        errors = field.check()
        self.assertEqual(errors, [
            Error('"choices" is not an iterable (e.g., a tuple or list).\n'
                '"choices" should be an iterable of pairs. The first element '
                'in each pair is the actual value to be stored, and '
                'the second element is the human-readable name. '
                'An example of a valid value is '
                '[("1", "first choice"), ("2", "second choice")].',
                hint=None, obj=field),
        ])

    def test_choices_containing_non_pairs(self):
        field = models.CharField(max_length=10, choices=[(1, 2, 3), (1, 2, 3)])
        errors = field.check()
        self.assertEqual(errors, [
            Error('Some items of "choices" are not pairs.\n'
                '"choices" should be an iterable of pairs. The first element '
                'in each pair is the actual value to be stored, and '
                'the second element is the human-readable name. '
                'An example of a valid value is '
                '[("1", "first choice"), ("2", "second choice")].',
                hint=None, obj=field),
        ])

    def test_bad_value_of_db_index(self):
        field = models.CharField(max_length=10, db_index='bad')
        errors = field.check()
        self.assertEqual(errors, [
            Error('Invalid "db_index" value (should be None, True or False).\n'
                'If set to True, a database index will be created for this '
                'field. ',
                hint='Set "db_index" to False or True or '
                'remove this optional argument.',
                obj=field),
        ])


class DecimalFieldTests(TestCase):

    def test_required_attributes(self):
        field = models.DecimalField()
        errors = field.check()
        self.assertEqual(errors, [
            Error('No "decimal_places" attribute.\n'
                'DecimalFields require a "decimal_places" attribute that is '
                'the number of decimal places to store with the number and is '
                'a non-negative integer smaller or equal to "max_digits". '
                'For example, if you set "decimal_places" to 2 then 1.23456 '
                'will be saved as 1.23.',
                hint=None, obj=field),
            Error('No "max_digits" attribute.\n'
                'DecimalFields require a "max_digits" attribute that is '
                'the maximum number of digits allowed in the number and '
                'is a positive integer greater or equal to "decimal_places". '
                'For example, if you set "max_digits" to 5 and '
                '"decimal_places" to 2 then 999.99 is the greatest number '
                'that you can save.',
                hint=None, obj=field),
        ])

    def test_negative_max_digits_and_decimal_places(self):
        field = models.DecimalField(max_digits=-1, decimal_places=-1)
        errors = field.check()
        self.assertEqual(errors, [
            Error('Invalid "decimal_places" value.\n'
                'DecimalFields require a "decimal_places" attribute that is '
                'the number of decimal places to store with the number and is '
                'a non-negative integer smaller or equal to "max_digits". '
                'For example, if you set "decimal_places" to 2 then 1.23456 '
                'will be saved as 1.23.',
                hint=None, obj=field),
            Error('Invalid "max_digits" value.\n'
                'DecimalFields require a "max_digits" attribute that is '
                'the maximum number of digits allowed in the number and '
                'is a positive integer greater or equal to "decimal_places". '
                'For example, if you set "max_digits" to 5 '
                'and "decimal_places" to 2 then 999.99 is the greatest number '
                'that you can save.',
                hint=None, obj=field),
        ])

    def test_bad_values_of_max_digits_and_decimal_places(self):
        field = models.DecimalField(max_digits="bad", decimal_places="bad")
        errors = field.check()
        self.assertEqual(errors, [
            Error('Invalid "decimal_places" value.\n'
                'DecimalFields require a "decimal_places" attribute that is '
                'the number of decimal places to store with the number and is '
                'a non-negative integer smaller or equal to "max_digits". '
                'For example, if you set "decimal_places" to 2 then 1.23456 '
                'will be saved as 1.23.',
                hint=None, obj=field),
            Error('Invalid "max_digits" value.\n'
                'DecimalFields require a "max_digits" attribute that is '
                'the maximum number of digits allowed in the number and '
                'is a positive integer greater or equal to "decimal_places". '
                'For example, if you set "max_digits" to 5 and '
                '"decimal_places" to 2 then 999.99 is the greatest number '
                'that you can save.',
                hint=None, obj=field),
        ])

    def test_decimal_places_greater_than_max_digits(self):
        field = models.DecimalField(max_digits=9, decimal_places=10)
        errors = field.check()
        self.assertEqual(errors, [
            Error('"max_digits" smaller than "decimal_places".\n'
                'DecimalFields require a "max_digits" argument that is '
                'the maximum number of digits allowed in the number and '
                'is a positive integer greater or equal to "decimal_places". '
                'For example, if you set "decimal_places" to 2 and you '
                'want to store numbers up to 999.99 then you should set '
                '"max_digits" to 5.',
                hint=None, obj=field),
        ])

    def test_valid_field(self):
        field = models.DecimalField(max_digits=10, decimal_places=10)
        self.assertEqual(field.check(), [])


class RelativeFieldTests(IsolatedModelsTestCase):

    def test_foreign_key_to_missing_model(self):
        # Model names are resolved when a model is being created, so we cannot
        # test relative fields in isolation and we need to attach them to a
        # model.
        class Model(models.Model):
            foreign_key = models.ForeignKey('Rel1')

        field = Model.foreign_key.field
        errors = field.check()
        self.assertEqual(errors, [
            Error('No Rel1 model or it is an abstract model.\n'
                'The field has a relation with model Rel1, which '
                'has either not been installed or is abstract.',
                hint='Ensure that you did not misspell the model name and '
                'the model is not abstract. Does your INSTALLED_APPS setting '
                'contain the app where Rel1 is defined?',
                obj=field),
        ])

    def test_many_to_many_to_missing_model(self):
        class Model(models.Model):
            m2m = models.ManyToManyField("Rel2")

        field = Model.m2m.field
        errors = field.check(from_model=Model)
        self.assertEqual(errors, [
            Error('No Rel2 model or it is an abstract model.\n'
                'The field has a many to many relation with model Rel2, '
                'which has either not been installed or is abstract.',
                hint='Ensure that you did not misspell the model name and '
                'the model is not abstract. Does your INSTALLED_APPS setting '
                'contain the app where Rel2 is defined?',
                obj=field),
        ])

    def test_ambiguous_relationship_model(self):

        class Person(models.Model):
            pass

        class Group(models.Model):
            field = models.ManyToManyField('Person',
                through="AmbiguousRelationship", related_name='tertiary')

        class AmbiguousRelationship(models.Model):
            # Too much foreign keys to Person.
            first_person = models.ForeignKey(Person, related_name="first")
            second_person = models.ForeignKey(Person, related_name="second")
            second_model = models.ForeignKey(Group)

        field = Group.field.field
        errors = field.check(from_model=Group)
        self.assertEqual(errors, [
            Error('More than one foreign key to Person in intermediary '
                'AmbiguousRelationship model.\n'
                'AmbiguousRelationship has more than one foreign key '
                'to Person, which is ambiguous and is not permitted.',
                hint='If you want to create a recursive relationship, use '
                'ForeignKey("self", symmetrical=False, '
                'through="AmbiguousRelationship").',
                obj=field),
        ])

    def test_relationship_model_with_foreign_key_to_wrong_model(self):
        class WrongModel(models.Model):
            pass

        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person',
                through="InvalidRelationship")

        class InvalidRelationship(models.Model):
            person = models.ForeignKey(Person)
            wrong_foreign_key = models.ForeignKey(WrongModel)
            # The last foreign key should point to Group model.

        field = Group.members.field
        errors = field.check(from_model=Group)
        self.assertEqual(errors, [
            Error('No foreign key to Group or Person '
                'in intermediary InvalidRelationship model.\n'
                'The field is a manually-defined many to many relation '
                'through model InvalidRelationship, which does not have '
                'foreign keys to Group or Person.\n',
                hint=None, obj=field),
        ])

    def test_relationship_model_missing_foreign_key(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person',
                through="InvalidRelationship")

        class InvalidRelationship(models.Model):
            group = models.ForeignKey(Group)
            # No foreign key to Person

        field = Group.members.field
        errors = field.check(from_model=Group)
        self.assertEqual(errors, [
            Error('No foreign key to Group or Person '
                'in intermediary InvalidRelationship model.\n'
                'The field is a manually-defined many to many relation '
                'through model InvalidRelationship, which does not have '
                'foreign keys to Group or Person.\n',
                hint=None, obj=field),
        ])

    def test_missing_relationship_model(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField('Person',
                through="MissingM2MModel")

        field = Group.members.field
        errors = field.check(from_model=Group)
        self.assertEqual(errors, [
            Error('No intermediary model MissingM2MModel.\n'
                'The field specifies a many-to-many relation through model '
                'MissingM2MModel, which has not been installed.',
                hint='Ensure that you did not misspell the model name and '
                'the model is not abstract. Does your INSTALLED_APPS setting '
                'contain the app where MissingM2MModel is defined?',
                obj=field),
        ])

    def test_symmetrical_self_referential_field(self):
        class Person(models.Model):
            # Implicit symmetrical=False.
            friends = models.ManyToManyField('self', through="Relationship")

        class Relationship(models.Model):
            first = models.ForeignKey(Person, related_name="rel_from_set")
            second = models.ForeignKey(Person, related_name="rel_to_set")

        field = Person.friends.field
        errors = field.check(from_model=Person)
        self.assertEqual(errors, [
            Error('Symmetrical field with intermediate table.\n'
                'Many-to-many fields with intermediate tables cannot '
                'be symmetrical.',
                hint=None, obj=field),
        ])

    def test_too_many_foreign_keys_in_self_referential_model(self):
        class Person(models.Model):
            friends = models.ManyToManyField('self',
                through="InvalidRelationship", symmetrical=False)

        class InvalidRelationship(models.Model):
            first = models.ForeignKey(Person, related_name="rel_from_set_2")
            second = models.ForeignKey(Person, related_name="rel_to_set_2")
            third = models.ForeignKey(Person, related_name="too_many_by_far")

        field = Person.friends.field
        errors = field.check(from_model=Person)
        self.assertEqual(errors, [
            Error('More than two foreign keys to Person '
                'in intermediary model InvalidRelationship.\n'
                'InvalidRelationship has more than two foreign keys to '
                'Person, which is ambiguous and is not permitted.',
                hint=None, obj=field),
        ])

    def test_symmetric_self_reference_with_intermediate_table(self):
        class Person(models.Model):
            # Explicit symmetrical=True.
            friends = models.ManyToManyField('self',
                through="Relationship", symmetrical=True)

        class Relationship(models.Model):
            first = models.ForeignKey(Person, related_name="rel_from_set")
            second = models.ForeignKey(Person, related_name="rel_to_set")

        field = Person.friends.field
        errors = field.check(from_model=Person)
        self.assertEqual(errors, [
            Error('Symmetrical field with intermediate table.\n'
                'Many-to-many fields with intermediate tables cannot '
                'be symmetrical.',
                hint=None, obj=field),
        ])

    def test_foreign_key_to_abstract_model(self):
        class Model(models.Model):
            foreign_key = models.ForeignKey('AbstractModel')

        class AbstractModel(models.Model):
            class Meta:
                abstract = True

        field = Model.foreign_key.field
        errors = field.check()
        self.assertEqual(errors, [
            Error('No AbstractModel model or it is an abstract model.\n'
                'The field has a relation with model AbstractModel, which '
                'has either not been installed or is abstract.',
                hint='Ensure that you did not misspell the model name and '
                'the model is not abstract. Does your INSTALLED_APPS setting '
                'contain the app where AbstractModel is defined?',
                obj=field),
        ])

    def test_m2m_to_abstract_model(self):
        class AbstractModel(models.Model):
            class Meta:
                abstract = True

        class Model(models.Model):
            m2m = models.ManyToManyField('AbstractModel')

        field = Model.m2m.field
        errors = field.check(from_model=Model)
        self.assertEqual(errors, [
            Error('No AbstractModel model or it is an abstract model.\n'
                'The field has a many to many relation with model '
                'AbstractModel, which has either not been installed '
                'or is abstract.',
                hint='Ensure that you did not misspell the model name and '
                'the model is not abstract. Does your INSTALLED_APPS setting '
                'contain the app where AbstractModel is defined?',
                obj=field),
        ])

    def test_unique_m2m(self):
        class Person(models.Model):
            name = models.CharField(max_length=5)

        class Group(models.Model):
            members = models.ManyToManyField('Person', unique=True)

        field = Group.members.field
        errors = field.check(from_model=Group)
        self.assertEqual(errors, [
            Error('Unique many-to-many field.\n'
                'ManyToManyFields cannot be unique.',
                hint=None, obj=field),
        ])

    def test_foreign_key_to_non_unique_field(self):
        class Target(models.Model):
            bad = models.IntegerField()  # No unique=True

        class Model(models.Model):
            foreign_key = models.ForeignKey('Target', to_field='bad')

        field = Model.foreign_key.field
        errors = field.check()
        self.assertEqual(errors, [
            Error('No unique=True constraint on field "bad" under model '
                'Target.\n'
                'The field "bad" has to be unique because a foreign key '
                'references to it.',
                hint=None, obj=field),
        ])

    def test_foreign_key_to_non_unique_field_under_explicit_model(self):
        class Target(models.Model):
            bad = models.IntegerField()

        # We don't need to attach the field to a model, because we pass Target
        # model explicitly.
        field = models.ForeignKey(Target, to_field='bad')
        errors = field.check()
        self.assertEqual(errors, [
            Error('No unique=True constraint on field "bad" under model '
                'Target.\n'
                'The field "bad" has to be unique because a foreign key '
                'references to it.',
                hint=None, obj=field),
        ])

    def test_on_delete_set_null_on_non_nullable_field(self):
        class Person(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey('Person',
                on_delete=models.SET_NULL)

        field = Model.foreign_key.field
        errors = field.check()
        self.assertEqual(errors, [
            Error('on_delete=SET_NULL but null forbidden.\n'
                'The field specifies on_delete=SET_NULL, but cannot be null.',
                hint='Set null=True argument on the field.',
                obj=field),
        ])

    def test_on_delete_set_default_without_default_value(self):
        class Person(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey('Person',
                on_delete=models.SET_DEFAULT)

        field = Model.foreign_key.field
        errors = field.check()
        self.assertEqual(errors, [
            Error('on_delete=SET_DEFAULT but no default value.\n'
                'The field specifies on_delete=SET_DEFAULT, but has '
                'no default value.',
                hint=None,
                obj=field),
        ])

    def test_nullable_primary_key(self):
        field = models.IntegerField(primary_key=True, null=True)
        errors = field.check()
        if connection.features.interprets_empty_strings_as_nulls:
            self.assertEqual(errors, [])
        else:
            self.assertEqual(errors, [
                Error('null=True for primary_key.\n'
                    'Primary key fields cannot have null=True.',
                    hint='Set null=False on the field or '
                    'remove primary_key=True argument.',
                    obj=field),
            ])

    def test_not_swapped_model(self):
        class SwappableModel(models.Model):
            # A model that can be, but isn't swapped out. References to this
            # model *shoudln't* raise any validation error.
            class Meta:
                swappable = 'TEST_SWAPPABLE_MODEL'

        class Model(models.Model):
            explicit_fk = models.ForeignKey(SwappableModel,
                related_name='explicit_fk')
            implicit_fk = models.ForeignKey('invalid_models.SwappableModel',
                related_name='implicit_fk')
            explicit_m2m = models.ManyToManyField(SwappableModel,
                related_name='explicit_m2m')
            implicit_m2m = models.ManyToManyField(
                'invalid_models.SwappableModel',
                related_name='implicit_m2m')

        explicit_fk = Model.explicit_fk.field
        self.assertEqual(explicit_fk.check(), [])

        implicit_fk = Model.implicit_fk.field
        self.assertEqual(implicit_fk.check(), [])

        explicit_m2m = Model.explicit_m2m.field
        self.assertEqual(explicit_m2m.check(from_model=Model), [])

        implicit_m2m = Model.implicit_m2m.field
        self.assertEqual(implicit_m2m.check(from_model=Model), [])

    @override_settings(TEST_SWAPPED_MODEL='invalid_models.Replacement')
    def test_referencing_to_swapped_model(self):
        class Replacement(models.Model):
            pass

        class SwappedModel(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL'

        class Model(models.Model):
            explicit_fk = models.ForeignKey(SwappedModel,
                related_name='explicit_fk')
            implicit_fk = models.ForeignKey('invalid_models.SwappedModel',
                related_name='implicit_fk')
            explicit_m2m = models.ManyToManyField(SwappedModel,
                related_name='explicit_m2m')
            implicit_m2m = models.ManyToManyField(
                'invalid_models.SwappedModel',
                related_name='implicit_m2m')

        fields = [
            Model.explicit_fk.field,
            Model.implicit_fk.field,
            Model.explicit_m2m.field,
            Model.implicit_m2m.field,
        ]

        expected_error = Error(
            'A relation with a swapped model.\n'
            'The field defines a relation with the model '
            'invalid_models.SwappedModel, which has been swapped out.',
            hint='Update the relation to point at '
            'settings.TEST_SWAPPED_MODEL')

        for field in fields:
            expected_error.obj = field
            errors = field.check(from_model=Model)
            self.assertEqual(errors, [expected_error])


class OtherFieldTests(TestCase):

    def test_missing_upload_to(self):
        field = models.FileField()
        errors = field.check()
        self.assertEqual(errors, [
            Error('No "upload_to" attribute.\n'
                'FileFields require an "upload_to" attribute.',
                hint=None, obj=field),
        ])

    def test_nullable_boolean_field(self):
        field = models.BooleanField(null=True)
        errors = field.check()
        self.assertEqual(errors, [
            Error('null=True for BooleanField.\n'
                'BooleanFields do not accept null values. Use '
                'a NullBooleanField instead.',
                hint=None, obj=field),
        ])

    def test_non_nullable_blank_GenericIPAddressField(self):
        field = models.GenericIPAddressField(null=False, blank=True)
        errors = field.check()
        self.assertEqual(errors, [
            Error('null=False and blank=True for GenericIPAddressField.\n'
                'GenericIPAddressField cannot accept blank values '
                'if null values are not allowed, as blank values are stored '
                'as null.',
                hint=None, obj=field),
        ])

    def test_FilePathField(self):
        field = models.FilePathField(allow_files=False, allow_folders=False)
        errors = field.check()
        self.assertEqual(errors, [
            Error('allow_files=False and allow_folders=False '
                'on FilePathField.\n'
                'FilePathFields must have either allow_files or allow_folders '
                'set to True.',
                hint=None, obj=field)
        ])

    def test_backend_specific_checks(self):
        error = Error('an error', hint=None)
        mock = lambda self, field, **kwargs: [error]

        # Mock connection.validation.check_field method.
        v = connection.validation
        old_check_field = v.check_field
        v.check_field = MethodType(mock, v)

        try:
            field = models.IntegerField()
            errors = field.check()
            self.assertEqual(errors, [error])
        finally:
            # Unmock connection.validation.check_field method.
            v.check_field = old_check_field


class AccessorClashTests(IsolatedModelsTestCase):

    def test_accessor_clash_fk_to_integer(self):
        self._test_accessor_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey('Target'))

    def test_accessor_clash_fk_to_fk(self):
        self._test_accessor_clash(
            target=models.ForeignKey('Another'),
            relative=models.ForeignKey('Target'))

    def test_accessor_clash_fk_to_m2m(self):
        self._test_accessor_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey('Target'))

    def test_accessor_clash_m2m_to_integer(self):
        self._test_accessor_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target'))

    def test_accessor_clash_m2m_to_fk(self):
        self._test_accessor_clash(
            target=models.ForeignKey('Another'),
            relative=models.ManyToManyField('Target'))

    def test_accessor_clash_m2m_to_m2m(self):
        self._test_accessor_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField('Target'))

    def _test_accessor_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            model_set = target

        class Model(models.Model):
            rel = relative

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Accessor for field Model.rel clashes with '
                'field Target.model_set.',
                hint='Rename field Target.model_set or add/change '
                'a related_name argument to the definition '
                'for field Model.rel.',
                obj=Model.rel.field),
        ])


class ReverseQueryNameClashTests(IsolatedModelsTestCase):

    def test_reverse_query_name_clash_fk_to_integer(self):
        self._test_reverse_query_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey('Target'))

    def test_reverse_query_name_clash_fk_to_fk(self):
        self._test_reverse_query_name_clash(
            target=models.ForeignKey('Another'),
            relative=models.ForeignKey('Target'))

    def test_reverse_query_name_clash_fk_to_m2m(self):
        self._test_reverse_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey('Target'))

    def test_reverse_query_name_clash_m2m_to_integer(self):
        self._test_reverse_query_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target'))

    def test_reverse_query_name_clash_m2m_to_fk(self):
        self._test_reverse_query_name_clash(
            target=models.ForeignKey('Another'),
            relative=models.ManyToManyField('Target'))

    def test_reverse_query_name_clash_m2m_to_m2m(self):
        self._test_reverse_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField('Target'))

    def _test_reverse_query_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            model = target

        class Model(models.Model):
            rel = relative

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Reverse query name for field Model.rel clashes '
                'with field Target.model.',
                hint='Rename field Target.model or add/change '
                'a related_name argument to the definition '
                'for field Model.rel.',
                obj=Model.rel.field),
        ])


class ExplicitRelatedNameClashTests(IsolatedModelsTestCase):

    def test_explicit_related_name_clash_fk_to_integer(self):
        self._test_explicit_related_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey('Target', related_name='clash'))

    def test_explicit_related_name_clash_fk_to_fk(self):
        self._test_explicit_related_name_clash(
            target=models.ForeignKey('Another'),
            relative=models.ForeignKey('Target', related_name='clash'))

    def test_explicit_related_name_clash_fk_to_m2m(self):
        self._test_explicit_related_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey('Target', related_name='clash'))

    def test_explicit_related_name_clash_m2m_to_integer(self):
        self._test_explicit_related_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target', related_name='clash'))

    def test_explicit_related_name_clash_m2m_to_fk(self):
        self._test_explicit_related_name_clash(
            target=models.ForeignKey('Another'),
            relative=models.ManyToManyField('Target', related_name='clash'))

    def test_explicit_related_name_clash_m2m_to_m2m(self):
        self._test_explicit_related_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField('Target', related_name='clash'))

    def _test_explicit_related_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            clash = target

        class Model(models.Model):
            rel = relative

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Accessor for field Model.rel clashes with '
                'field Target.clash.',
                hint='Rename field Target.clash or add/change '
                'a related_name argument to the definition '
                'for field Model.rel.',
                obj=Model.rel.field),
            Error('Reverse query name for field Model.rel clashes with '
                'field Target.clash.',
                hint='Rename field Target.clash or add/change '
                'a related_name argument to the definition '
                'for field Model.rel.',
                obj=Model.rel.field),
        ])


class ExplicitRelatedQueryNameClashTests(IsolatedModelsTestCase):

    def test_explicit_related_query_name_clash_fk_to_integer(self):
        self._test_explicit_related_query_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey('Target',
                related_query_name='clash'))

    def test_explicit_related_query_name_clash_fk_to_fk(self):
        self._test_explicit_related_query_name_clash(
            target=models.ForeignKey('Another'),
            relative=models.ForeignKey('Target',
                related_query_name='clash'))

    def test_explicit_related_query_name_clash_fk_to_m2m(self):
        self._test_explicit_related_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ForeignKey('Target',
                related_query_name='clash'))

    def test_explicit_related_query_name_clash_m2m_to_integer(self):
        self._test_explicit_related_query_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField('Target',
                related_query_name='clash'))

    def test_explicit_related_query_name_clash_m2m_to_fk(self):
        self._test_explicit_related_query_name_clash(
            target=models.ForeignKey('Another'),
            relative=models.ManyToManyField('Target',
                related_query_name='clash'))

    def test_explicit_related_query_name_clash_m2m_to_m2m(self):
        self._test_explicit_related_query_name_clash(
            target=models.ManyToManyField('Another'),
            relative=models.ManyToManyField('Target',
                related_query_name='clash'))

    def _test_explicit_related_query_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            clash = target

        class Model(models.Model):
            rel = relative

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Reverse query name for field Model.rel clashes with '
                'field Target.clash.',
                hint='Rename field Target.clash or add/change a related_name '
                'argument to the definition for field Model.rel.',
                obj=Model.rel.field)
        ])


class SelfReferentialM2MClashTests(IsolatedModelsTestCase):

    def test_self_m2m_clash(self):
        class Model(models.Model):
            first_m2m = models.ManyToManyField('self', symmetrical=False)
            second_m2m = models.ManyToManyField('self', symmetrical=False)

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Clash between accessors for Model.first_m2m '
                'and Model.second_m2m.',
                hint=u'Add or change a related_name argument '
                'to the definition for Model.first_m2m or Model.second_m2m.',
                obj=Model.first_m2m.field),
            Error('Clash between accessors for Model.second_m2m '
                'and Model.first_m2m.',
                hint=u'Add or change a related_name argument '
                'to the definition for Model.second_m2m or Model.first_m2m.',
                obj=Model.second_m2m.field),
        ])

    def test_self_m2m_accessor_clash(self):
        class Model(models.Model):
            model_set = models.ManyToManyField("self", symmetrical=False)

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Accessor for field Model.model_set clashes with '
                'field Model.model_set.',
                hint='Rename field Model.model_set or add/change '
                'a related_name argument to the definition '
                'for field Model.model_set.',
                obj=Model._meta.get_field('model_set'))
        ])

    def test_self_m2m_reverse_query_name_clash(self):
        class Model(models.Model):
            model = models.ManyToManyField("self", symmetrical=False)

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Reverse query name for field Model.model clashes with '
                'field Model.model.',
                hint='Rename field Model.model or add/change a related_name '
                'argument to the definition for field Model.model.',
                obj=Model._meta.get_field('model'))
        ])

    def test_self_m2m_clash_explicit_related_name(self):
        class Model(models.Model):
            clash = models.IntegerField()
            m2m = models.ManyToManyField("self",
                symmetrical=False, related_name='clash')

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Accessor for field Model.m2m clashes with '
                'field Model.clash.',
                hint='Rename field Model.clash or add/change a related_name '
                'argument to the definition for field Model.m2m.',
                obj=Model.m2m.field),
            Error('Reverse query name for field Model.m2m clashes with '
                'field Model.clash.',
                hint='Rename field Model.clash or add/change a related_name '
                'argument to the definition for field Model.m2m.',
                obj=Model.m2m.field),
        ])

    def test_valid_self_m2m(self):
        class Model(models.Model):
            first = models.ManyToManyField("self",
                symmetrical=False, related_name='first_accessor')
            second = models.ManyToManyField("self",
                symmetrical=False, related_name='second_accessor')

        errors = Model.check()
        self.assertEqual(errors, [])


class OtherClashTests(IsolatedModelsTestCase):

    def test_clash_between_accessors(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            foreign = models.ForeignKey(Target)
            m2m = models.ManyToManyField(Target)

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Clash between accessors for Model.foreign and Model.m2m.',
                hint='Add or change a related_name argument to the definition '
                'for Model.foreign or Model.m2m.',
                obj=Model.foreign.field),
            Error('Clash between accessors for Model.m2m and Model.foreign.',
                hint='Add or change a related_name argument to the definition '
                'for Model.m2m or Model.foreign.',
                obj=Model.m2m.field),
        ])

    def test_self_clash_accessor(self):
        class Model(models.Model):
            model_set = models.ForeignKey("Model")

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Accessor for field Model.model_set clashes with '
                'field Model.model_set.',
                hint='Rename field Model.model_set or add/change '
                'a related_name argument to the definition '
                'for field Model.model_set.',
                obj=Model._meta.get_field('model_set')),
        ])

    def test_self_clash_reverse_query_name(self):
        class Model(models.Model):
            model = models.ForeignKey("Model")

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Reverse query name for field Model.model clashes with '
                'field Model.model.',
                hint='Rename field Model.model or add/change '
                'a related_name argument to the definition '
                'for field Model.model.',
                obj=Model._meta.get_field('model')),
        ])

    def test_self_clash_explicit_related_name(self):
        class Model(models.Model):
            clash = models.CharField(max_length=10)
            foreign = models.ForeignKey("Model", related_name='clash')

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Accessor for field Model.foreign clashes with '
                'field Model.clash.',
                hint='Rename field Model.clash or add/change '
                'a related_name argument to the definition '
                'for field Model.foreign.',
                obj=Model.foreign.field),
            Error('Reverse query name for field Model.foreign clashes with '
                'field Model.clash.',
                hint='Rename field Model.clash or add/change '
                'a related_name argument to the definition '
                'for field Model.foreign.',
                obj=Model.foreign.field),
        ])

    def test_complex_clash(self):
        class Target(models.Model):
            tgt_safe = models.CharField(max_length=10)
            clash = models.CharField(max_length=10)
            model = models.CharField(max_length=10)

            clash1_set = models.CharField(max_length=10)

        class Model(models.Model):
            src_safe = models.CharField(max_length=10)

            foreign_1 = models.ForeignKey(Target, related_name='id')
            foreign_2 = models.ForeignKey(Target, related_name='src_safe')

            m2m_1 = models.ManyToManyField(Target, related_name='id')
            m2m_2 = models.ManyToManyField(Target, related_name='src_safe')

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Accessor for field Model.foreign_1 clashes with '
                'field Target.id.',
                hint='Rename field Target.id or add/change a related_name '
                'argument to the definition for field Model.foreign_1.',
                obj=Model.foreign_1.field),
            Error('Reverse query name for field Model.foreign_1 clashes with '
                'field Target.id.',
                hint='Rename field Target.id or add/change a related_name '
                'argument to the definition for field Model.foreign_1.',
                obj=Model.foreign_1.field),
            Error('Clash between accessors for Model.foreign_1 '
                'and Model.m2m_1.',
                hint='Add or change a related_name argument to '
                'the definition for Model.foreign_1 or Model.m2m_1.',
                obj=Model.foreign_1.field),
            Error('Clash between reverse query names for Model.foreign_1 '
                'and Model.m2m_1.',
                hint='Add or change a related_name argument to '
                'the definition for Model.foreign_1 or Model.m2m_1.',
                obj=Model.foreign_1.field),

            Error('Clash between accessors for Model.foreign_2 '
                'and Model.m2m_2.',
                hint='Add or change a related_name argument '
                'to the definition for Model.foreign_2 or Model.m2m_2.',
                obj=Model.foreign_2.field),
            Error('Clash between reverse query names for Model.foreign_2 '
                'and Model.m2m_2.',
                hint='Add or change a related_name argument to '
                'the definition for Model.foreign_2 or Model.m2m_2.',
                obj=Model.foreign_2.field),

            Error('Accessor for field Model.m2m_1 clashes with '
                'field Target.id.',
                hint='Rename field Target.id or add/change a related_name '
                'argument to the definition for field Model.m2m_1.',
                obj=Model.m2m_1.field),
            Error('Reverse query name for field Model.m2m_1 clashes with '
                'field Target.id.',
                hint='Rename field Target.id or add/change a related_name '
                'argument to the definition for field Model.m2m_1.',
                obj=Model.m2m_1.field),
            Error('Clash between accessors for Model.m2m_1 '
                'and Model.foreign_1.',
                hint='Add or change a related_name argument to the definition '
                'for Model.m2m_1 or Model.foreign_1.',
                obj=Model.m2m_1.field),
            Error('Clash between reverse query names for Model.m2m_1 '
                'and Model.foreign_1.',
                hint='Add or change a related_name argument to '
                'the definition for Model.m2m_1 or Model.foreign_1.',
                obj=Model.m2m_1.field),

            Error('Clash between accessors for Model.m2m_2 '
                'and Model.foreign_2.',
                hint='Add or change a related_name argument to the definition '
                'for Model.m2m_2 or Model.foreign_2.',
                obj=Model.m2m_2.field),
            Error('Clash between reverse query names for Model.m2m_2 '
                'and Model.foreign_2.',
                hint='Add or change a related_name argument to the definition '
                'for Model.m2m_2 or Model.foreign_2.',
                obj=Model.m2m_2.field),
        ])


class IndexAndUniqueTogetherTests(IsolatedModelsTestCase):

    def test_index_together_not_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = 'not-a-list'

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Non-iterable "index_together".\n'
                '"index_together" is a list of field names that, taken '
                'together, are indexed, so "index_together" must be '
                'an iterable (e.g. a list). ',
                hint=None, obj=Model),
        ])

    def test_index_together_containing_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = [
                    'non-iterable',
                    'second-non-iterable',
                ]

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Some items of "index_together" are not iterable '
                '(e.g. a list).\n'
                '"index_together" is a list of field names '
                '(which are nested lists) that, taken together, are '
                'indexed, so "index_together" must be an iterable '
                'of iterables (i. e. a list of lists), i. e. '
                '[["first_field", "second_field"]].',
                hint=None, obj=Model),
        ])

    def test_index_together_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                index_together = [
                    ["missing_field"],
                ]

        errors = Model.check()
        self.assertEqual(errors, [
            Error('"index_together" pointing to a missing "missing_field" '
                'field.\n'
                'Model.index_together points to a field "missing_field" '
                'which does not exist.',
                hint='Ensure that you did not misspell the field name.',
                obj=Model),
        ])

    def test_index_together_pointing_to_m2m(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                index_together = [
                    ["m2m"],
                ]

        errors = Model.check()
        self.assertEqual(errors, [
            Error('"index_together" referring to a m2m "m2m" field.\n'
                'ManyToManyFields are not supported in '
                '"index_together".',
                hint=None, obj=Model)
        ])

    def test_unique_together_not_iterable(self):
        class Model(models.Model):
            class Meta:
                unique_together = 'not-a-list'

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Non-iterable "unique_together".\n'
                '"unique_together" is a list of field names that, taken '
                'together, are indexed, so "unique_together" must be '
                'an iterable (e.g. a list).',
                hint=None, obj=Model),
        ])

    def test_unique_together_containing_non_iterable(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                unique_together = [('a', 'b'), 'not-a-list']

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Some items of "unique_together" are not iterable '
                '(e.g. a list).\n'
                '"unique_together" is a list of field names '
                '(which are nested lists) that, taken together, are '
                'indexed, so "unique_together" must be an iterable '
                'of iterables (i. e. a list of tuples), i. e. '
                '[("first_field", "second_field")]. When dealing with '
                'a single set of fields, a single tuple can be used: '
                '("first_field", "second_field").',
                hint=None, obj=Model),
        ])

    def test_valid_unique_together(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                # unique_together can be a simple tuple
                unique_together = ('one', 'two')

        errors = Model.check()
        self.assertEqual(errors, [])

    def test_unique_together_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                unique_together = [
                    ["missing_field"],
                ]

        errors = Model.check()
        self.assertEqual(errors, [
            Error('"unique_together" pointing to a missing "missing_field" '
                'field.\n'
                'Model.unique_together points to a field "missing_field" '
                'which does not exist.',
                hint='Ensure that you did not misspell the field name.',
                obj=Model),
        ])

    def test_unique_together_pointing_to_m2m(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                unique_together = [
                    ["m2m"],
                ]

        errors = Model.check()
        self.assertEqual(errors, [
            Error('"unique_together" referring to a m2m "m2m" field.\n'
                'ManyToManyFields are not supported in '
                '"unique_together".',
                hint=None, obj=Model)
        ])


class OtherModelTests(IsolatedModelsTestCase):

    def test_unique_primary_key(self):
        class Model(models.Model):
            id = models.IntegerField(primary_key=False)

        errors = Model.check()
        self.assertEqual(errors, [
            Error('"id" field is not a primary key.\n'
                'You cannot use "id" as a field name, '
                'because each model automatically gets an "id" field '
                'if none of the fields have primary_key=True.',
                hint='Remove or rename "id" field or '
                'add primary_key=True to a field.',
                obj=Model)
        ])

    def test_field_names_ending_with_underscore(self):
        class Model(models.Model):
            field_ = models.CharField(max_length=10)
            m2m_ = models.ManyToManyField('self')

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Field name ending with an underscore.\n'
                'Field names cannot end with underscores, because this '
                'would lead to ambiguous queryset filters.',
                hint=None, obj=Model._meta.get_field('field_')),
            Error('Field name ending with an underscore.\n'
                'Field names cannot end with underscores, because this '
                'would lead to ambiguous queryset filters.',
                hint=None, obj=Model._meta.get_field('m2m_')),
        ])

    def test_ordering_non_iterable(self):
        class Model(models.Model):
            class Meta:
                ordering = "missing_field"

        errors = Model.check()
        self.assertEqual(errors, [
            Error('Non iterable "ordering".\n'
                '"ordering" must be a tuple or list of field names, i. e. '
                '["pub_date", "author"]. If you want to order by only one '
                'field, you still need to use a list, i. e. ["pub_date"].',
                hint=None, obj=Model)
        ])

    def test_ordering_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                ordering = ("missing_field",)

        errors = Model.check()
        self.assertEqual(errors, [
            Error('"ordering" pointing to a missing "missing_field" field.',
                hint='Ensure that you did not misspell the field name.',
                obj=Model)
        ])

    @override_settings(TEST_SWAPPED_MODEL_BAD_VALUE='not-a-model')
    def test_swappable_missing_app_name(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_VALUE'

        errors = Model.check()
        self.assertEqual(errors, [
            Error('"TEST_SWAPPED_MODEL_BAD_VALUE" is not of the form '
                '"app_label.app_name".',
                hint=None, obj=Model)
        ])

    @override_settings(TEST_SWAPPED_MODEL_BAD_MODEL='not_an_app.Target')
    def test_swappable_missing_app(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_MODEL'

        errors = Model.check()
        self.assertEqual(errors, [
            Error('not_an_app.Target not installed or abstract.\n'
                'The model has been swapped out for not_an_app.Target which '
                'has not been installed or is abstract.',
                hint='Ensure that you did not misspell the model name and '
                'the app name as well as the model is not abstract. Does your '
                'INSTALLED_APPS setting contain the "not_an_app" app?',
                obj=Model)
        ])

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
        self.assertEqual(errors, [
            Error('Two m2m relations through the same model.\n'
                'The model has two many-to-many relations through '
                'the intermediary Membership model, which is not permitted.',
                hint=None,
                obj=Group)
        ])
