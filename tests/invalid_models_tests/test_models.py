# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import warnings

from django.conf import settings
from django.core.checks import Error
from django.db import connections, models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps, override_settings


def get_max_column_name_length():
    allowed_len = None
    db_alias = None

    for db in settings.DATABASES.keys():
        connection = connections[db]
        max_name_length = connection.ops.max_name_length()
        if max_name_length is None or connection.features.truncates_names:
            continue
        else:
            if allowed_len is None:
                allowed_len = max_name_length
                db_alias = db
            elif max_name_length < allowed_len:
                allowed_len = max_name_length
                db_alias = db

    return (allowed_len, db_alias)


@isolate_apps('invalid_models_tests')
class IndexTogetherTests(SimpleTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = 42

        errors = Model.check()
        expected = [
            Error(
                "'index_together' must be a list or tuple.",
                obj=Model,
                id='models.E008',
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
                "'index_together' must be a list or tuple.",
                obj=Model,
                id='models.E008',
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
                "All 'index_together' elements must be lists or tuples.",
                obj=Model,
                id='models.E009',
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
                "'index_together' refers to the non-existent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_pointing_to_non_local_field(self):
        class Foo(models.Model):
            field1 = models.IntegerField()

        class Bar(Foo):
            field2 = models.IntegerField()

            class Meta:
                index_together = [
                    ["field2", "field1"],
                ]

        errors = Bar.check()
        expected = [
            Error(
                "'index_together' refers to field 'field1' which is not "
                "local to model 'Bar'.",
                hint=("This issue may be caused by multi-table inheritance."),
                obj=Bar,
                id='models.E016',
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
                "'index_together' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'index_together'.",
                obj=Model,
                id='models.E013',
            ),
        ]
        self.assertEqual(errors, expected)


# unique_together tests are very similar to index_together tests.
@isolate_apps('invalid_models_tests')
class UniqueTogetherTests(SimpleTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                unique_together = 42

        errors = Model.check()
        expected = [
            Error(
                "'unique_together' must be a list or tuple.",
                obj=Model,
                id='models.E010',
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
                "All 'unique_together' elements must be lists or tuples.",
                obj=Model,
                id='models.E011',
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
                "'unique_together' must be a list or tuple.",
                obj=Model,
                id='models.E010',
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
                "'unique_together' refers to the non-existent field 'missing_field'.",
                obj=Model,
                id='models.E012',
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
                "'unique_together' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'unique_together'.",
                obj=Model,
                id='models.E013',
            ),
        ]
        self.assertEqual(errors, expected)


@isolate_apps('invalid_models_tests')
class FieldNamesTests(SimpleTestCase):

    def test_ending_with_underscore(self):
        class Model(models.Model):
            field_ = models.CharField(max_length=10)
            m2m_ = models.ManyToManyField('self')

        errors = Model.check()
        expected = [
            Error(
                'Field names must not end with an underscore.',
                obj=Model._meta.get_field('field_'),
                id='fields.E001',
            ),
            Error(
                'Field names must not end with an underscore.',
                obj=Model._meta.get_field('m2m_'),
                id='fields.E001',
            ),
        ]
        self.assertEqual(errors, expected)

    max_column_name_length, column_limit_db_alias = get_max_column_name_length()

    @unittest.skipIf(max_column_name_length is None, "The database doesn't have a column name length limit.")
    def test_M2M_long_column_name(self):
        """
        #13711 -- Model check for long M2M column names when database has
        column name length limits.
        """
        allowed_len, db_alias = get_max_column_name_length()

        # A model with very long name which will be used to set relations to.
        class VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz(models.Model):
            title = models.CharField(max_length=11)

        # Main model for which checks will be performed.
        class ModelWithLongField(models.Model):
            m2m_field = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name="rn1"
            )
            m2m_field2 = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name="rn2", through='m2msimple'
            )
            m2m_field3 = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name="rn3",
                through='m2mcomplex'
            )
            fk = models.ForeignKey(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                models.CASCADE,
                related_name="rn4",
            )

        # Models used for setting `through` in M2M field.
        class m2msimple(models.Model):
            id2 = models.ForeignKey(ModelWithLongField, models.CASCADE)

        class m2mcomplex(models.Model):
            id2 = models.ForeignKey(ModelWithLongField, models.CASCADE)

        long_field_name = 'a' * (self.max_column_name_length + 1)
        models.ForeignKey(
            VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
            models.CASCADE,
        ).contribute_to_class(m2msimple, long_field_name)

        models.ForeignKey(
            VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
            models.CASCADE,
            db_column=long_field_name
        ).contribute_to_class(m2mcomplex, long_field_name)

        errors = ModelWithLongField.check()

        # First error because of M2M field set on the model with long name.
        m2m_long_name = "verylongmodelnamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz_id"
        if self.max_column_name_length > len(m2m_long_name):
            # Some databases support names longer than the test name.
            expected = []
        else:
            expected = [
                Error(
                    'Autogenerated column name too long for M2M field "%s". '
                    'Maximum length is "%s" for database "%s".'
                    % (m2m_long_name, self.max_column_name_length, self.column_limit_db_alias),
                    hint="Use 'through' to create a separate model for "
                         "M2M and then set column_name using 'db_column'.",
                    obj=ModelWithLongField,
                    id='models.E019',
                )
            ]

        # Second error because the FK specified in the `through` model
        # `m2msimple` has auto-generated name longer than allowed.
        # There will be no check errors in the other M2M because it
        # specifies db_column for the FK in `through` model even if the actual
        # name is longer than the limits of the database.
        expected.append(
            Error(
                'Autogenerated column name too long for M2M field "%s_id". '
                'Maximum length is "%s" for database "%s".'
                % (long_field_name, self.max_column_name_length, self.column_limit_db_alias),
                hint="Use 'through' to create a separate model for "
                     "M2M and then set column_name using 'db_column'.",
                obj=ModelWithLongField,
                id='models.E019',
            )
        )

        self.assertEqual(errors, expected)

    @unittest.skipIf(max_column_name_length is None, "The database doesn't have a column name length limit.")
    def test_local_field_long_column_name(self):
        """
        #13711 -- Model check for long column names
        when database does not support long names.
        """
        allowed_len, db_alias = get_max_column_name_length()

        class ModelWithLongField(models.Model):
            title = models.CharField(max_length=11)

        long_field_name = 'a' * (self.max_column_name_length + 1)
        long_field_name2 = 'b' * (self.max_column_name_length + 1)
        models.CharField(max_length=11).contribute_to_class(ModelWithLongField, long_field_name)
        models.CharField(max_length=11, db_column='vlmn').contribute_to_class(ModelWithLongField, long_field_name2)

        errors = ModelWithLongField.check()

        # Error because of the field with long name added to the model
        # without specifying db_column
        expected = [
            Error(
                'Autogenerated column name too long for field "%s". '
                'Maximum length is "%s" for database "%s".'
                % (long_field_name, self.max_column_name_length, self.column_limit_db_alias),
                hint="Set the column name manually using 'db_column'.",
                obj=ModelWithLongField,
                id='models.E018',
            )
        ]

        self.assertEqual(errors, expected)

    def test_including_separator(self):
        class Model(models.Model):
            some__field = models.IntegerField()

        errors = Model.check()
        expected = [
            Error(
                'Field names must not contain "__".',
                obj=Model._meta.get_field('some__field'),
                id='fields.E002',
            )
        ]
        self.assertEqual(errors, expected)

    def test_pk(self):
        class Model(models.Model):
            pk = models.IntegerField()

        errors = Model.check()
        expected = [
            Error(
                "'pk' is a reserved word that cannot be used as a field name.",
                obj=Model._meta.get_field('pk'),
                id='fields.E003',
            )
        ]
        self.assertEqual(errors, expected)


@isolate_apps('invalid_models_tests')
class ShadowingFieldsTests(SimpleTestCase):

    def test_field_name_clash_with_child_accessor(self):
        class Parent(models.Model):
            pass

        class Child(Parent):
            child = models.CharField(max_length=100)

        errors = Child.check()
        expected = [
            Error(
                "The field 'child' clashes with the field "
                "'child' from model 'invalid_models_tests.parent'.",
                obj=Child._meta.get_field('child'),
                id='models.E006',
            )
        ]
        self.assertEqual(errors, expected)

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
                "The field 'id' from parent model "
                "'invalid_models_tests.mother' clashes with the field 'id' "
                "from parent model 'invalid_models_tests.father'.",
                obj=Child,
                id='models.E005',
            ),
            Error(
                "The field 'clash' from parent model "
                "'invalid_models_tests.mother' clashes with the field 'clash' "
                "from parent model 'invalid_models_tests.father'.",
                obj=Child,
                id='models.E005',
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
            f = models.ForeignKey(Target, models.CASCADE)

        errors = Child.check()
        expected = [
            Error(
                "The field 'f' clashes with the field 'f_id' "
                "from model 'invalid_models_tests.parent'.",
                obj=Child._meta.get_field('f'),
                id='models.E006',
            )
        ]
        self.assertEqual(errors, expected)

    def test_multigeneration_inheritance(self):
        class GrandParent(models.Model):
            clash = models.IntegerField()

        class Parent(GrandParent):
            pass

        class Child(Parent):
            pass

        class GrandChild(Child):
            clash = models.IntegerField()

        errors = GrandChild.check()
        expected = [
            Error(
                "The field 'clash' clashes with the field 'clash' "
                "from model 'invalid_models_tests.grandparent'.",
                obj=GrandChild._meta.get_field('clash'),
                id='models.E006',
            )
        ]
        self.assertEqual(errors, expected)

    def test_id_clash(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk = models.ForeignKey(Target, models.CASCADE)
            fk_id = models.IntegerField()

        errors = Model.check()
        expected = [
            Error(
                "The field 'fk_id' clashes with the field 'fk' from model "
                "'invalid_models_tests.model'.",
                obj=Model._meta.get_field('fk_id'),
                id='models.E006',
            )
        ]
        self.assertEqual(errors, expected)


@isolate_apps('invalid_models_tests')
class OtherModelTests(SimpleTestCase):

    def test_unique_primary_key(self):
        invalid_id = models.IntegerField(primary_key=False)

        class Model(models.Model):
            id = invalid_id

        errors = Model.check()
        expected = [
            Error(
                "'id' can only be used as a field name if the field also sets "
                "'primary_key=True'.",
                obj=Model,
                id='models.E004',
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
                "'ordering' must be a tuple or list "
                "(even if you want to order by only one field).",
                obj=Model,
                id='models.E014',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_just_ordering_no_errors(self):
        class Model(models.Model):
            order = models.PositiveIntegerField()

            class Meta:
                ordering = ['order']

        self.assertEqual(Model.check(), [])

    def test_just_order_with_respect_to_no_errors(self):
        class Question(models.Model):
            pass

        class Answer(models.Model):
            question = models.ForeignKey(Question, models.CASCADE)

            class Meta:
                order_with_respect_to = 'question'

        self.assertEqual(Answer.check(), [])

    def test_ordering_with_order_with_respect_to(self):
        class Question(models.Model):
            pass

        class Answer(models.Model):
            question = models.ForeignKey(Question, models.CASCADE)
            order = models.IntegerField()

            class Meta:
                order_with_respect_to = 'question'
                ordering = ['order']

        errors = Answer.check()
        expected = [
            Error(
                "'ordering' and 'order_with_respect_to' cannot be used together.",
                obj=Answer,
                id='models.E021',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_non_valid(self):
        class RelationModel(models.Model):
            pass

        class Model(models.Model):
            relation = models.ManyToManyField(RelationModel)

            class Meta:
                ordering = ['relation']

        errors = Model.check()
        expected = [
            Error(
                "'ordering' refers to the non-existent field 'relation'.",
                obj=Model,
                id='models.E015',
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
                "'ordering' refers to the non-existent field 'missing_field'.",
                obj=Model,
                id='models.E015',
            )
        ]
        self.assertEqual(errors, expected)

    def test_ordering_pointing_to_missing_foreignkey_field(self):
        # refs #22711

        class Model(models.Model):
            missing_fk_field = models.IntegerField()

            class Meta:
                ordering = ("missing_fk_field_id",)

        errors = Model.check()
        expected = [
            Error(
                "'ordering' refers to the non-existent field 'missing_fk_field_id'.",
                obj=Model,
                id='models.E015',
            )
        ]
        self.assertEqual(errors, expected)

    def test_ordering_pointing_to_existing_foreignkey_field(self):
        # refs #22711

        class Parent(models.Model):
            pass

        class Child(models.Model):
            parent = models.ForeignKey(Parent, models.CASCADE)

            class Meta:
                ordering = ("parent_id",)

        self.assertFalse(Child.check())

    @override_settings(TEST_SWAPPED_MODEL_BAD_VALUE='not-a-model')
    def test_swappable_missing_app_name(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_VALUE'

        errors = Model.check()
        expected = [
            Error(
                "'TEST_SWAPPED_MODEL_BAD_VALUE' is not of the form 'app_label.app_name'.",
                id='models.E001',
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
                "'TEST_SWAPPED_MODEL_BAD_MODEL' references 'not_an_app.Target', "
                'which has not been installed, or is abstract.',
                id='models.E002',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_two_m2m_through_same_relationship(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            primary = models.ManyToManyField(Person, through="Membership", related_name="primary")
            secondary = models.ManyToManyField(Person, through="Membership", related_name="secondary")

        class Membership(models.Model):
            person = models.ForeignKey(Person, models.CASCADE)
            group = models.ForeignKey(Group, models.CASCADE)

        errors = Group.check()
        expected = [
            Error(
                "The model has two many-to-many relations through "
                "the intermediate model 'invalid_models_tests.Membership'.",
                obj=Group,
                id='models.E003',
            )
        ]
        self.assertEqual(errors, expected)

    def test_missing_parent_link(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')

            class Place(models.Model):
                pass

            class ParkingLot(Place):
                # In lieu of any other connector, an existing OneToOneField will be
                # promoted to the primary key.
                parent = models.OneToOneField(Place, models.CASCADE)

        self.assertEqual(len(warns), 1)
        msg = str(warns[0].message)
        self.assertEqual(
            msg,
            'Add parent_link=True to invalid_models_tests.ParkingLot.parent '
            'as an implicit link is deprecated.'
        )
        self.assertEqual(ParkingLot._meta.pk.name, 'parent')
