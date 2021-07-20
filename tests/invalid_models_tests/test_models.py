import unittest

from django.core.checks import Error, Warning
from django.core.checks.model_checks import _check_lazy_references
from django.db import connection, connections, models
from django.db.models.functions import Abs, Lower, Round
from django.db.models.signals import post_init
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps, override_settings, register_lookup


class EmptyRouter:
    pass


def get_max_column_name_length():
    allowed_len = None
    db_alias = None

    for db in ('default', 'other'):
        connection = connections[db]
        max_name_length = connection.ops.max_name_length()
        if max_name_length is not None and not connection.features.truncates_names:
            if allowed_len is None or max_name_length < allowed_len:
                allowed_len = max_name_length
                db_alias = db

    return (allowed_len, db_alias)


@isolate_apps('invalid_models_tests')
class IndexTogetherTests(SimpleTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = 42

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' must be a list or tuple.",
                obj=Model,
                id='models.E008',
            ),
        ])

    def test_non_list(self):
        class Model(models.Model):
            class Meta:
                index_together = 'not-a-list'

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' must be a list or tuple.",
                obj=Model,
                id='models.E008',
            ),
        ])

    def test_list_containing_non_iterable(self):
        class Model(models.Model):
            class Meta:
                index_together = [('a', 'b'), 42]

        self.assertEqual(Model.check(), [
            Error(
                "All 'index_together' elements must be lists or tuples.",
                obj=Model,
                id='models.E009',
            ),
        ])

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                index_together = [['missing_field']]

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_pointing_to_non_local_field(self):
        class Foo(models.Model):
            field1 = models.IntegerField()

        class Bar(Foo):
            field2 = models.IntegerField()

            class Meta:
                index_together = [['field2', 'field1']]

        self.assertEqual(Bar.check(), [
            Error(
                "'index_together' refers to field 'field1' which is not "
                "local to model 'Bar'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Bar,
                id='models.E016',
            ),
        ])

    def test_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                index_together = [['m2m']]

        self.assertEqual(Model.check(), [
            Error(
                "'index_together' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'index_together'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    def test_pointing_to_fk(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foo_1 = models.ForeignKey(Foo, on_delete=models.CASCADE, related_name='bar_1')
            foo_2 = models.ForeignKey(Foo, on_delete=models.CASCADE, related_name='bar_2')

            class Meta:
                index_together = [['foo_1_id', 'foo_2']]

        self.assertEqual(Bar.check(), [])


# unique_together tests are very similar to index_together tests.
@isolate_apps('invalid_models_tests')
class UniqueTogetherTests(SimpleTestCase):

    def test_non_iterable(self):
        class Model(models.Model):
            class Meta:
                unique_together = 42

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' must be a list or tuple.",
                obj=Model,
                id='models.E010',
            ),
        ])

    def test_list_containing_non_iterable(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                unique_together = [('a', 'b'), 42]

        self.assertEqual(Model.check(), [
            Error(
                "All 'unique_together' elements must be lists or tuples.",
                obj=Model,
                id='models.E011',
            ),
        ])

    def test_non_list(self):
        class Model(models.Model):
            class Meta:
                unique_together = 'not-a-list'

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' must be a list or tuple.",
                obj=Model,
                id='models.E010',
            ),
        ])

    def test_valid_model(self):
        class Model(models.Model):
            one = models.IntegerField()
            two = models.IntegerField()

            class Meta:
                # unique_together can be a simple tuple
                unique_together = ('one', 'two')

        self.assertEqual(Model.check(), [])

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                unique_together = [['missing_field']]

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_pointing_to_m2m(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                unique_together = [['m2m']]

        self.assertEqual(Model.check(), [
            Error(
                "'unique_together' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'unique_together'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    def test_pointing_to_fk(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foo_1 = models.ForeignKey(Foo, on_delete=models.CASCADE, related_name='bar_1')
            foo_2 = models.ForeignKey(Foo, on_delete=models.CASCADE, related_name='bar_2')

            class Meta:
                unique_together = [['foo_1_id', 'foo_2']]

        self.assertEqual(Bar.check(), [])


@isolate_apps('invalid_models_tests')
class IndexesTests(TestCase):

    def test_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                indexes = [models.Index(fields=['missing_field'], name='name')]

        self.assertEqual(Model.check(), [
            Error(
                "'indexes' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                indexes = [models.Index(fields=['m2m'], name='name')]

        self.assertEqual(Model.check(), [
            Error(
                "'indexes' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'indexes'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    def test_pointing_to_non_local_field(self):
        class Foo(models.Model):
            field1 = models.IntegerField()

        class Bar(Foo):
            field2 = models.IntegerField()

            class Meta:
                indexes = [models.Index(fields=['field2', 'field1'], name='name')]

        self.assertEqual(Bar.check(), [
            Error(
                "'indexes' refers to field 'field1' which is not local to "
                "model 'Bar'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Bar,
                id='models.E016',
            ),
        ])

    def test_pointing_to_fk(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foo_1 = models.ForeignKey(Foo, on_delete=models.CASCADE, related_name='bar_1')
            foo_2 = models.ForeignKey(Foo, on_delete=models.CASCADE, related_name='bar_2')

            class Meta:
                indexes = [models.Index(fields=['foo_1_id', 'foo_2'], name='index_name')]

        self.assertEqual(Bar.check(), [])

    def test_name_constraints(self):
        class Model(models.Model):
            class Meta:
                indexes = [
                    models.Index(fields=['id'], name='_index_name'),
                    models.Index(fields=['id'], name='5index_name'),
                ]

        self.assertEqual(Model.check(), [
            Error(
                "The index name '%sindex_name' cannot start with an "
                "underscore or a number." % prefix,
                obj=Model,
                id='models.E033',
            ) for prefix in ('_', '5')
        ])

    def test_max_name_length(self):
        index_name = 'x' * 31

        class Model(models.Model):
            class Meta:
                indexes = [models.Index(fields=['id'], name=index_name)]

        self.assertEqual(Model.check(), [
            Error(
                "The index name '%s' cannot be longer than 30 characters."
                % index_name,
                obj=Model,
                id='models.E034',
            ),
        ])

    def test_index_with_condition(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                indexes = [
                    models.Index(
                        fields=['age'],
                        name='index_age_gte_10',
                        condition=models.Q(age__gte=10),
                    ),
                ]

        errors = Model.check(databases=self.databases)
        expected = [] if connection.features.supports_partial_indexes else [
            Warning(
                '%s does not support indexes with conditions.'
                % connection.display_name,
                hint=(
                    "Conditions will be ignored. Silence this warning if you "
                    "don't care about it."
                ),
                obj=Model,
                id='models.W037',
            )
        ]
        self.assertEqual(errors, expected)

    def test_index_with_condition_required_db_features(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                required_db_features = {'supports_partial_indexes'}
                indexes = [
                    models.Index(
                        fields=['age'],
                        name='index_age_gte_10',
                        condition=models.Q(age__gte=10),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    def test_index_with_include(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                indexes = [
                    models.Index(
                        fields=['age'],
                        name='index_age_include_id',
                        include=['id'],
                    ),
                ]

        errors = Model.check(databases=self.databases)
        expected = [] if connection.features.supports_covering_indexes else [
            Warning(
                '%s does not support indexes with non-key columns.'
                % connection.display_name,
                hint=(
                    "Non-key columns will be ignored. Silence this warning if "
                    "you don't care about it."
                ),
                obj=Model,
                id='models.W040',
            )
        ]
        self.assertEqual(errors, expected)

    def test_index_with_include_required_db_features(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                required_db_features = {'supports_covering_indexes'}
                indexes = [
                    models.Index(
                        fields=['age'],
                        name='index_age_include_id',
                        include=['id'],
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_index_include_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                indexes = [
                    models.Index(fields=['id'], include=['missing_field'], name='name'),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'indexes' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_index_include_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                indexes = [models.Index(fields=['id'], include=['m2m'], name='name')]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'indexes' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'indexes'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_index_include_pointing_to_non_local_field(self):
        class Parent(models.Model):
            field1 = models.IntegerField()

        class Child(Parent):
            field2 = models.IntegerField()

            class Meta:
                indexes = [
                    models.Index(fields=['field2'], include=['field1'], name='name'),
                ]

        self.assertEqual(Child.check(databases=self.databases), [
            Error(
                "'indexes' refers to field 'field1' which is not local to "
                "model 'Child'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Child,
                id='models.E016',
            ),
        ])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_index_include_pointing_to_fk(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk_1 = models.ForeignKey(Target, models.CASCADE, related_name='target_1')
            fk_2 = models.ForeignKey(Target, models.CASCADE, related_name='target_2')

            class Meta:
                constraints = [
                    models.Index(
                        fields=['id'],
                        include=['fk_1_id', 'fk_2'],
                        name='name',
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    def test_func_index(self):
        class Model(models.Model):
            name = models.CharField(max_length=10)

            class Meta:
                indexes = [models.Index(Lower('name'), name='index_lower_name')]

        warn = Warning(
            '%s does not support indexes on expressions.'
            % connection.display_name,
            hint=(
                "An index won't be created. Silence this warning if you don't "
                "care about it."
            ),
            obj=Model,
            id='models.W043',
        )
        expected = [] if connection.features.supports_expression_indexes else [warn]
        self.assertEqual(Model.check(databases=self.databases), expected)

    def test_func_index_required_db_features(self):
        class Model(models.Model):
            name = models.CharField(max_length=10)

            class Meta:
                indexes = [models.Index(Lower('name'), name='index_lower_name')]
                required_db_features = {'supports_expression_indexes'}

        self.assertEqual(Model.check(databases=self.databases), [])

    def test_func_index_complex_expression_custom_lookup(self):
        class Model(models.Model):
            height = models.IntegerField()
            weight = models.IntegerField()

            class Meta:
                indexes = [
                    models.Index(
                        models.F('height') / (models.F('weight__abs') + models.Value(5)),
                        name='name',
                    ),
                ]

        with register_lookup(models.IntegerField, Abs):
            self.assertEqual(Model.check(), [])

    def test_func_index_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                indexes = [models.Index(Lower('missing_field').desc(), name='name')]

        self.assertEqual(Model.check(), [
            Error(
                "'indexes' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_func_index_pointing_to_missing_field_nested(self):
        class Model(models.Model):
            class Meta:
                indexes = [
                    models.Index(Abs(Round('missing_field')), name='name'),
                ]

        self.assertEqual(Model.check(), [
            Error(
                "'indexes' refers to the nonexistent field 'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_func_index_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                indexes = [models.Index(Lower('m2m'), name='name')]

        self.assertEqual(Model.check(), [
            Error(
                "'indexes' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'indexes'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    def test_func_index_pointing_to_non_local_field(self):
        class Foo(models.Model):
            field1 = models.CharField(max_length=15)

        class Bar(Foo):
            class Meta:
                indexes = [models.Index(Lower('field1'), name='name')]

        self.assertEqual(Bar.check(), [
            Error(
                "'indexes' refers to field 'field1' which is not local to "
                "model 'Bar'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Bar,
                id='models.E016',
            ),
        ])

    def test_func_index_pointing_to_fk(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foo_1 = models.ForeignKey(Foo, models.CASCADE, related_name='bar_1')
            foo_2 = models.ForeignKey(Foo, models.CASCADE, related_name='bar_2')

            class Meta:
                indexes = [
                    models.Index(Lower('foo_1_id'), Lower('foo_2'), name='index_name'),
                ]

        self.assertEqual(Bar.check(), [])


@isolate_apps('invalid_models_tests')
class FieldNamesTests(TestCase):
    databases = {'default', 'other'}

    def test_ending_with_underscore(self):
        class Model(models.Model):
            field_ = models.CharField(max_length=10)
            m2m_ = models.ManyToManyField('self')

        self.assertEqual(Model.check(), [
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
        ])

    max_column_name_length, column_limit_db_alias = get_max_column_name_length()

    @unittest.skipIf(max_column_name_length is None, "The database doesn't have a column name length limit.")
    def test_M2M_long_column_name(self):
        """
        #13711 -- Model check for long M2M column names when database has
        column name length limits.
        """
        # A model with very long name which will be used to set relations to.
        class VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz(models.Model):
            title = models.CharField(max_length=11)

        # Main model for which checks will be performed.
        class ModelWithLongField(models.Model):
            m2m_field = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name='rn1',
            )
            m2m_field2 = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name='rn2', through='m2msimple',
            )
            m2m_field3 = models.ManyToManyField(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                related_name='rn3',
                through='m2mcomplex',
            )
            fk = models.ForeignKey(
                VeryLongModelNamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz,
                models.CASCADE,
                related_name='rn4',
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

        errors = ModelWithLongField.check(databases=('default', 'other'))

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
        # Check for long column names is called only for specified database
        # aliases.
        self.assertEqual(ModelWithLongField.check(databases=None), [])

    @unittest.skipIf(max_column_name_length is None, "The database doesn't have a column name length limit.")
    def test_local_field_long_column_name(self):
        """
        #13711 -- Model check for long column names
        when database does not support long names.
        """
        class ModelWithLongField(models.Model):
            title = models.CharField(max_length=11)

        long_field_name = 'a' * (self.max_column_name_length + 1)
        long_field_name2 = 'b' * (self.max_column_name_length + 1)
        models.CharField(max_length=11).contribute_to_class(ModelWithLongField, long_field_name)
        models.CharField(max_length=11, db_column='vlmn').contribute_to_class(ModelWithLongField, long_field_name2)
        self.assertEqual(ModelWithLongField.check(databases=('default', 'other')), [
            Error(
                'Autogenerated column name too long for field "%s". '
                'Maximum length is "%s" for database "%s".'
                % (long_field_name, self.max_column_name_length, self.column_limit_db_alias),
                hint="Set the column name manually using 'db_column'.",
                obj=ModelWithLongField,
                id='models.E018',
            )
        ])
        # Check for long column names is called only for specified database
        # aliases.
        self.assertEqual(ModelWithLongField.check(databases=None), [])

    def test_including_separator(self):
        class Model(models.Model):
            some__field = models.IntegerField()

        self.assertEqual(Model.check(), [
            Error(
                'Field names must not contain "__".',
                obj=Model._meta.get_field('some__field'),
                id='fields.E002',
            )
        ])

    def test_pk(self):
        class Model(models.Model):
            pk = models.IntegerField()

        self.assertEqual(Model.check(), [
            Error(
                "'pk' is a reserved word that cannot be used as a field name.",
                obj=Model._meta.get_field('pk'),
                id='fields.E003',
            )
        ])

    def test_db_column_clash(self):
        class Model(models.Model):
            foo = models.IntegerField()
            bar = models.IntegerField(db_column='foo')

        self.assertEqual(Model.check(), [
            Error(
                "Field 'bar' has column name 'foo' that is used by "
                "another field.",
                hint="Specify a 'db_column' for the field.",
                obj=Model,
                id='models.E007',
            )
        ])


@isolate_apps('invalid_models_tests')
class ShadowingFieldsTests(SimpleTestCase):

    def test_field_name_clash_with_child_accessor(self):
        class Parent(models.Model):
            pass

        class Child(Parent):
            child = models.CharField(max_length=100)

        self.assertEqual(Child.check(), [
            Error(
                "The field 'child' clashes with the field "
                "'child' from model 'invalid_models_tests.parent'.",
                obj=Child._meta.get_field('child'),
                id='models.E006',
            )
        ])

    def test_field_name_clash_with_m2m_through(self):
        class Parent(models.Model):
            clash_id = models.IntegerField()

        class Child(Parent):
            clash = models.ForeignKey('Child', models.CASCADE)

        class Model(models.Model):
            parents = models.ManyToManyField(
                to=Parent,
                through='Through',
                through_fields=['parent', 'model'],
            )

        class Through(models.Model):
            parent = models.ForeignKey(Parent, models.CASCADE)
            model = models.ForeignKey(Model, models.CASCADE)

        self.assertEqual(Child.check(), [
            Error(
                "The field 'clash' clashes with the field 'clash_id' from "
                "model 'invalid_models_tests.parent'.",
                obj=Child._meta.get_field('clash'),
                id='models.E006',
            )
        ])

    def test_multiinheritance_clash(self):
        class Mother(models.Model):
            clash = models.IntegerField()

        class Father(models.Model):
            clash = models.IntegerField()

        class Child(Mother, Father):
            # Here we have two clashed: id (automatic field) and clash, because
            # both parents define these fields.
            pass

        self.assertEqual(Child.check(), [
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
        ])

    def test_inheritance_clash(self):
        class Parent(models.Model):
            f_id = models.IntegerField()

        class Target(models.Model):
            # This field doesn't result in a clash.
            f_id = models.IntegerField()

        class Child(Parent):
            # This field clashes with parent "f_id" field.
            f = models.ForeignKey(Target, models.CASCADE)

        self.assertEqual(Child.check(), [
            Error(
                "The field 'f' clashes with the field 'f_id' "
                "from model 'invalid_models_tests.parent'.",
                obj=Child._meta.get_field('f'),
                id='models.E006',
            )
        ])

    def test_multigeneration_inheritance(self):
        class GrandParent(models.Model):
            clash = models.IntegerField()

        class Parent(GrandParent):
            pass

        class Child(Parent):
            pass

        class GrandChild(Child):
            clash = models.IntegerField()

        self.assertEqual(GrandChild.check(), [
            Error(
                "The field 'clash' clashes with the field 'clash' "
                "from model 'invalid_models_tests.grandparent'.",
                obj=GrandChild._meta.get_field('clash'),
                id='models.E006',
            )
        ])

    def test_id_clash(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk = models.ForeignKey(Target, models.CASCADE)
            fk_id = models.IntegerField()

        self.assertEqual(Model.check(), [
            Error(
                "The field 'fk_id' clashes with the field 'fk' from model "
                "'invalid_models_tests.model'.",
                obj=Model._meta.get_field('fk_id'),
                id='models.E006',
            )
        ])


@isolate_apps('invalid_models_tests')
class OtherModelTests(SimpleTestCase):

    def test_unique_primary_key(self):
        invalid_id = models.IntegerField(primary_key=False)

        class Model(models.Model):
            id = invalid_id

        self.assertEqual(Model.check(), [
            Error(
                "'id' can only be used as a field name if the field also sets "
                "'primary_key=True'.",
                obj=Model,
                id='models.E004',
            ),
        ])

    def test_ordering_non_iterable(self):
        class Model(models.Model):
            class Meta:
                ordering = 'missing_field'

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' must be a tuple or list "
                "(even if you want to order by only one field).",
                obj=Model,
                id='models.E014',
            ),
        ])

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

        self.assertEqual(Answer.check(), [
            Error(
                "'ordering' and 'order_with_respect_to' cannot be used together.",
                obj=Answer,
                id='models.E021',
            ),
        ])

    def test_non_valid(self):
        class RelationModel(models.Model):
            pass

        class Model(models.Model):
            relation = models.ManyToManyField(RelationModel)

            class Meta:
                ordering = ['relation']

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'relation'.",
                obj=Model,
                id='models.E015',
            ),
        ])

    def test_ordering_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                ordering = ('missing_field',)

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'missing_field'.",
                obj=Model,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_to_missing_foreignkey_field(self):
        class Model(models.Model):
            missing_fk_field = models.IntegerField()

            class Meta:
                ordering = ('missing_fk_field_id',)

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'missing_fk_field_id'.",
                obj=Model,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_to_missing_related_field(self):
        class Model(models.Model):
            test = models.IntegerField()

            class Meta:
                ordering = ('missing_related__id',)

        self.assertEqual(Model.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'missing_related__id'.",
                obj=Model,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_to_missing_related_model_field(self):
        class Parent(models.Model):
            pass

        class Child(models.Model):
            parent = models.ForeignKey(Parent, models.CASCADE)

            class Meta:
                ordering = ('parent__missing_field',)

        self.assertEqual(Child.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'parent__missing_field'.",
                obj=Child,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_to_non_related_field(self):
        class Child(models.Model):
            parent = models.IntegerField()

            class Meta:
                ordering = ('parent__missing_field',)

        self.assertEqual(Child.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'parent__missing_field'.",
                obj=Child,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_to_two_related_model_field(self):
        class Parent2(models.Model):
            pass

        class Parent1(models.Model):
            parent2 = models.ForeignKey(Parent2, models.CASCADE)

        class Child(models.Model):
            parent1 = models.ForeignKey(Parent1, models.CASCADE)

            class Meta:
                ordering = ('parent1__parent2__missing_field',)

        self.assertEqual(Child.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'parent1__parent2__missing_field'.",
                obj=Child,
                id='models.E015',
            )
        ])

    def test_ordering_pointing_multiple_times_to_model_fields(self):
        class Parent(models.Model):
            field1 = models.CharField(max_length=100)
            field2 = models.CharField(max_length=100)

        class Child(models.Model):
            parent = models.ForeignKey(Parent, models.CASCADE)

            class Meta:
                ordering = ('parent__field1__field2',)

        self.assertEqual(Child.check(), [
            Error(
                "'ordering' refers to the nonexistent field, related field, "
                "or lookup 'parent__field1__field2'.",
                obj=Child,
                id='models.E015',
            )
        ])

    def test_ordering_allows_registered_lookups(self):
        class Model(models.Model):
            test = models.CharField(max_length=100)

            class Meta:
                ordering = ('test__lower',)

        with register_lookup(models.CharField, Lower):
            self.assertEqual(Model.check(), [])

    def test_ordering_pointing_to_lookup_not_transform(self):
        class Model(models.Model):
            test = models.CharField(max_length=100)

            class Meta:
                ordering = ('test__isnull',)

        self.assertEqual(Model.check(), [])

    def test_ordering_pointing_to_related_model_pk(self):
        class Parent(models.Model):
            pass

        class Child(models.Model):
            parent = models.ForeignKey(Parent, models.CASCADE)

            class Meta:
                ordering = ('parent__pk',)

        self.assertEqual(Child.check(), [])

    def test_ordering_pointing_to_foreignkey_field(self):
        class Parent(models.Model):
            pass

        class Child(models.Model):
            parent = models.ForeignKey(Parent, models.CASCADE)

            class Meta:
                ordering = ('parent_id',)

        self.assertFalse(Child.check())

    def test_name_beginning_with_underscore(self):
        class _Model(models.Model):
            pass

        self.assertEqual(_Model.check(), [
            Error(
                "The model name '_Model' cannot start or end with an underscore "
                "as it collides with the query lookup syntax.",
                obj=_Model,
                id='models.E023',
            )
        ])

    def test_name_ending_with_underscore(self):
        class Model_(models.Model):
            pass

        self.assertEqual(Model_.check(), [
            Error(
                "The model name 'Model_' cannot start or end with an underscore "
                "as it collides with the query lookup syntax.",
                obj=Model_,
                id='models.E023',
            )
        ])

    def test_name_contains_double_underscores(self):
        class Test__Model(models.Model):
            pass

        self.assertEqual(Test__Model.check(), [
            Error(
                "The model name 'Test__Model' cannot contain double underscores "
                "as it collides with the query lookup syntax.",
                obj=Test__Model,
                id='models.E024',
            )
        ])

    def test_property_and_related_field_accessor_clash(self):
        class Model(models.Model):
            fk = models.ForeignKey('self', models.CASCADE)

            @property
            def fk_id(self):
                pass

        self.assertEqual(Model.check(), [
            Error(
                "The property 'fk_id' clashes with a related field accessor.",
                obj=Model,
                id='models.E025',
            )
        ])

    def test_single_primary_key(self):
        class Model(models.Model):
            foo = models.IntegerField(primary_key=True)
            bar = models.IntegerField(primary_key=True)

        self.assertEqual(Model.check(), [
            Error(
                "The model cannot have more than one field with 'primary_key=True'.",
                obj=Model,
                id='models.E026',
            )
        ])

    @override_settings(TEST_SWAPPED_MODEL_BAD_VALUE='not-a-model')
    def test_swappable_missing_app_name(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_VALUE'

        self.assertEqual(Model.check(), [
            Error(
                "'TEST_SWAPPED_MODEL_BAD_VALUE' is not of the form 'app_label.app_name'.",
                id='models.E001',
            ),
        ])

    @override_settings(TEST_SWAPPED_MODEL_BAD_MODEL='not_an_app.Target')
    def test_swappable_missing_app(self):
        class Model(models.Model):
            class Meta:
                swappable = 'TEST_SWAPPED_MODEL_BAD_MODEL'

        self.assertEqual(Model.check(), [
            Error(
                "'TEST_SWAPPED_MODEL_BAD_MODEL' references 'not_an_app.Target', "
                'which has not been installed, or is abstract.',
                id='models.E002',
            ),
        ])

    def test_two_m2m_through_same_relationship(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            primary = models.ManyToManyField(Person, through='Membership', related_name='primary')
            secondary = models.ManyToManyField(Person, through='Membership', related_name='secondary')

        class Membership(models.Model):
            person = models.ForeignKey(Person, models.CASCADE)
            group = models.ForeignKey(Group, models.CASCADE)

        self.assertEqual(Group.check(), [
            Error(
                "The model has two identical many-to-many relations through "
                "the intermediate model 'invalid_models_tests.Membership'.",
                obj=Group,
                id='models.E003',
            )
        ])

    def test_two_m2m_through_same_model_with_different_through_fields(self):
        class Country(models.Model):
            pass

        class ShippingMethod(models.Model):
            to_countries = models.ManyToManyField(
                Country, through='ShippingMethodPrice',
                through_fields=('method', 'to_country'),
            )
            from_countries = models.ManyToManyField(
                Country, through='ShippingMethodPrice',
                through_fields=('method', 'from_country'),
                related_name='+',
            )

        class ShippingMethodPrice(models.Model):
            method = models.ForeignKey(ShippingMethod, models.CASCADE)
            to_country = models.ForeignKey(Country, models.CASCADE)
            from_country = models.ForeignKey(Country, models.CASCADE)

        self.assertEqual(ShippingMethod.check(), [])

    def test_onetoone_with_parent_model(self):
        class Place(models.Model):
            pass

        class ParkingLot(Place):
            other_place = models.OneToOneField(Place, models.CASCADE, related_name='other_parking')

        self.assertEqual(ParkingLot.check(), [])

    def test_onetoone_with_explicit_parent_link_parent_model(self):
        class Place(models.Model):
            pass

        class ParkingLot(Place):
            place = models.OneToOneField(Place, models.CASCADE, parent_link=True, primary_key=True)
            other_place = models.OneToOneField(Place, models.CASCADE, related_name='other_parking')

        self.assertEqual(ParkingLot.check(), [])

    def test_m2m_table_name_clash(self):
        class Foo(models.Model):
            bar = models.ManyToManyField('Bar', db_table='myapp_bar')

            class Meta:
                db_table = 'myapp_foo'

        class Bar(models.Model):
            class Meta:
                db_table = 'myapp_bar'

        self.assertEqual(Foo.check(), [
            Error(
                "The field's intermediary table 'myapp_bar' clashes with the "
                "table name of 'invalid_models_tests.Bar'.",
                obj=Foo._meta.get_field('bar'),
                id='fields.E340',
            )
        ])

    @override_settings(DATABASE_ROUTERS=['invalid_models_tests.test_models.EmptyRouter'])
    def test_m2m_table_name_clash_database_routers_installed(self):
        class Foo(models.Model):
            bar = models.ManyToManyField('Bar', db_table='myapp_bar')

            class Meta:
                db_table = 'myapp_foo'

        class Bar(models.Model):
            class Meta:
                db_table = 'myapp_bar'

        self.assertEqual(Foo.check(), [
            Warning(
                "The field's intermediary table 'myapp_bar' clashes with the "
                "table name of 'invalid_models_tests.Bar'.",
                obj=Foo._meta.get_field('bar'),
                hint=(
                    "You have configured settings.DATABASE_ROUTERS. Verify "
                    "that the table of 'invalid_models_tests.Bar' is "
                    "correctly routed to a separate database."
                ),
                id='fields.W344',
            ),
        ])

    def test_m2m_field_table_name_clash(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foos = models.ManyToManyField(Foo, db_table='clash')

        class Baz(models.Model):
            foos = models.ManyToManyField(Foo, db_table='clash')

        self.assertEqual(Bar.check() + Baz.check(), [
            Error(
                "The field's intermediary table 'clash' clashes with the "
                "table name of 'invalid_models_tests.Baz.foos'.",
                obj=Bar._meta.get_field('foos'),
                id='fields.E340',
            ),
            Error(
                "The field's intermediary table 'clash' clashes with the "
                "table name of 'invalid_models_tests.Bar.foos'.",
                obj=Baz._meta.get_field('foos'),
                id='fields.E340',
            )
        ])

    @override_settings(DATABASE_ROUTERS=['invalid_models_tests.test_models.EmptyRouter'])
    def test_m2m_field_table_name_clash_database_routers_installed(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foos = models.ManyToManyField(Foo, db_table='clash')

        class Baz(models.Model):
            foos = models.ManyToManyField(Foo, db_table='clash')

        self.assertEqual(Bar.check() + Baz.check(), [
            Warning(
                "The field's intermediary table 'clash' clashes with the "
                "table name of 'invalid_models_tests.%s.foos'."
                % clashing_model,
                obj=model_cls._meta.get_field('foos'),
                hint=(
                    "You have configured settings.DATABASE_ROUTERS. Verify "
                    "that the table of 'invalid_models_tests.%s.foos' is "
                    "correctly routed to a separate database." % clashing_model
                ),
                id='fields.W344',
            ) for model_cls, clashing_model in [(Bar, 'Baz'), (Baz, 'Bar')]
        ])

    def test_m2m_autogenerated_table_name_clash(self):
        class Foo(models.Model):
            class Meta:
                db_table = 'bar_foos'

        class Bar(models.Model):
            # The autogenerated `db_table` will be bar_foos.
            foos = models.ManyToManyField(Foo)

            class Meta:
                db_table = 'bar'

        self.assertEqual(Bar.check(), [
            Error(
                "The field's intermediary table 'bar_foos' clashes with the "
                "table name of 'invalid_models_tests.Foo'.",
                obj=Bar._meta.get_field('foos'),
                id='fields.E340',
            )
        ])

    @override_settings(DATABASE_ROUTERS=['invalid_models_tests.test_models.EmptyRouter'])
    def test_m2m_autogenerated_table_name_clash_database_routers_installed(self):
        class Foo(models.Model):
            class Meta:
                db_table = 'bar_foos'

        class Bar(models.Model):
            # The autogenerated db_table is bar_foos.
            foos = models.ManyToManyField(Foo)

            class Meta:
                db_table = 'bar'

        self.assertEqual(Bar.check(), [
            Warning(
                "The field's intermediary table 'bar_foos' clashes with the "
                "table name of 'invalid_models_tests.Foo'.",
                obj=Bar._meta.get_field('foos'),
                hint=(
                    "You have configured settings.DATABASE_ROUTERS. Verify "
                    "that the table of 'invalid_models_tests.Foo' is "
                    "correctly routed to a separate database."
                ),
                id='fields.W344',
            ),
        ])

    def test_m2m_unmanaged_shadow_models_not_checked(self):
        class A1(models.Model):
            pass

        class C1(models.Model):
            mm_a = models.ManyToManyField(A1, db_table='d1')

        # Unmanaged models that shadow the above models. Reused table names
        # shouldn't be flagged by any checks.
        class A2(models.Model):
            class Meta:
                managed = False

        class C2(models.Model):
            mm_a = models.ManyToManyField(A2, through='Intermediate')

            class Meta:
                managed = False

        class Intermediate(models.Model):
            a2 = models.ForeignKey(A2, models.CASCADE, db_column='a1_id')
            c2 = models.ForeignKey(C2, models.CASCADE, db_column='c1_id')

            class Meta:
                db_table = 'd1'
                managed = False

        self.assertEqual(C1.check(), [])
        self.assertEqual(C2.check(), [])

    def test_m2m_to_concrete_and_proxy_allowed(self):
        class A(models.Model):
            pass

        class Through(models.Model):
            a = models.ForeignKey('A', models.CASCADE)
            c = models.ForeignKey('C', models.CASCADE)

        class ThroughProxy(Through):
            class Meta:
                proxy = True

        class C(models.Model):
            mm_a = models.ManyToManyField(A, through=Through)
            mm_aproxy = models.ManyToManyField(A, through=ThroughProxy, related_name='proxied_m2m')

        self.assertEqual(C.check(), [])

    @isolate_apps('django.contrib.auth', kwarg_name='apps')
    def test_lazy_reference_checks(self, apps):
        class DummyModel(models.Model):
            author = models.ForeignKey('Author', models.CASCADE)

            class Meta:
                app_label = 'invalid_models_tests'

        class DummyClass:
            def __call__(self, **kwargs):
                pass

            def dummy_method(self):
                pass

        def dummy_function(*args, **kwargs):
            pass

        apps.lazy_model_operation(dummy_function, ('auth', 'imaginarymodel'))
        apps.lazy_model_operation(dummy_function, ('fanciful_app', 'imaginarymodel'))

        post_init.connect(dummy_function, sender='missing-app.Model', apps=apps)
        post_init.connect(DummyClass(), sender='missing-app.Model', apps=apps)
        post_init.connect(DummyClass().dummy_method, sender='missing-app.Model', apps=apps)

        self.assertEqual(_check_lazy_references(apps), [
            Error(
                "%r contains a lazy reference to auth.imaginarymodel, "
                "but app 'auth' doesn't provide model 'imaginarymodel'." % dummy_function,
                obj=dummy_function,
                id='models.E022',
            ),
            Error(
                "%r contains a lazy reference to fanciful_app.imaginarymodel, "
                "but app 'fanciful_app' isn't installed." % dummy_function,
                obj=dummy_function,
                id='models.E022',
            ),
            Error(
                "An instance of class 'DummyClass' was connected to "
                "the 'post_init' signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='invalid_models_tests.test_models',
                id='signals.E001',
            ),
            Error(
                "Bound method 'DummyClass.dummy_method' was connected to the "
                "'post_init' signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='invalid_models_tests.test_models',
                id='signals.E001',
            ),
            Error(
                "The field invalid_models_tests.DummyModel.author was declared "
                "with a lazy reference to 'invalid_models_tests.author', but app "
                "'invalid_models_tests' isn't installed.",
                hint=None,
                obj=DummyModel.author.field,
                id='fields.E307',
            ),
            Error(
                "The function 'dummy_function' was connected to the 'post_init' "
                "signal with a lazy reference to the sender "
                "'missing-app.model', but app 'missing-app' isn't installed.",
                hint=None,
                obj='invalid_models_tests.test_models',
                id='signals.E001',
            ),
        ])


@isolate_apps('invalid_models_tests')
class JSONFieldTests(TestCase):
    @skipUnlessDBFeature('supports_json_field')
    def test_ordering_pointing_to_json_field_value(self):
        class Model(models.Model):
            field = models.JSONField()

            class Meta:
                ordering = ['field__value']

        self.assertEqual(Model.check(databases=self.databases), [])

    def test_check_jsonfield(self):
        class Model(models.Model):
            field = models.JSONField()

        error = Error(
            '%s does not support JSONFields.' % connection.display_name,
            obj=Model,
            id='fields.E180',
        )
        expected = [] if connection.features.supports_json_field else [error]
        self.assertEqual(Model.check(databases=self.databases), expected)

    def test_check_jsonfield_required_db_features(self):
        class Model(models.Model):
            field = models.JSONField()

            class Meta:
                required_db_features = {'supports_json_field'}

        self.assertEqual(Model.check(databases=self.databases), [])


@isolate_apps('invalid_models_tests')
class ConstraintsTests(TestCase):
    def test_check_constraints(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                constraints = [models.CheckConstraint(check=models.Q(age__gte=18), name='is_adult')]

        errors = Model.check(databases=self.databases)
        warn = Warning(
            '%s does not support check constraints.' % connection.display_name,
            hint=(
                "A constraint won't be created. Silence this warning if you "
                "don't care about it."
            ),
            obj=Model,
            id='models.W027',
        )
        expected = [] if connection.features.supports_table_check_constraints else [warn]
        self.assertCountEqual(errors, expected)

    def test_check_constraints_required_db_features(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                required_db_features = {'supports_table_check_constraints'}
                constraints = [models.CheckConstraint(check=models.Q(age__gte=18), name='is_adult')]
        self.assertEqual(Model.check(databases=self.databases), [])

    def test_check_constraint_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                required_db_features = {'supports_table_check_constraints'}
                constraints = [
                    models.CheckConstraint(
                        name='name', check=models.Q(missing_field=2),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the nonexistent field "
                "'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ] if connection.features.supports_table_check_constraints else [])

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_reverse_fk(self):
        class Model(models.Model):
            parent = models.ForeignKey('self', models.CASCADE, related_name='parents')

            class Meta:
                constraints = [
                    models.CheckConstraint(name='name', check=models.Q(parents=3)),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the nonexistent field 'parents'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_reverse_o2o(self):
        class Model(models.Model):
            parent = models.OneToOneField('self', models.CASCADE)

            class Meta:
                constraints = [
                    models.CheckConstraint(
                        name='name',
                        check=models.Q(model__isnull=True),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the nonexistent field 'model'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                constraints = [
                    models.CheckConstraint(name='name', check=models.Q(m2m=2)),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'constraints'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_fk(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk_1 = models.ForeignKey(Target, models.CASCADE, related_name='target_1')
            fk_2 = models.ForeignKey(Target, models.CASCADE, related_name='target_2')

            class Meta:
                constraints = [
                    models.CheckConstraint(
                        name='name',
                        check=models.Q(fk_1_id=2) | models.Q(fk_2=2),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_pk(self):
        class Model(models.Model):
            age = models.SmallIntegerField()

            class Meta:
                constraints = [
                    models.CheckConstraint(
                        name='name',
                        check=models.Q(pk__gt=5) & models.Q(age__gt=models.F('pk')),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_non_local_field(self):
        class Parent(models.Model):
            field1 = models.IntegerField()

        class Child(Parent):
            pass

            class Meta:
                constraints = [
                    models.CheckConstraint(name='name', check=models.Q(field1=1)),
                ]

        self.assertEqual(Child.check(databases=self.databases), [
            Error(
                "'constraints' refers to field 'field1' which is not local to "
                "model 'Child'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Child,
                id='models.E016',
            ),
        ])

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_joined_fields(self):
        class Model(models.Model):
            name = models.CharField(max_length=10)
            field1 = models.PositiveSmallIntegerField()
            field2 = models.PositiveSmallIntegerField()
            field3 = models.PositiveSmallIntegerField()
            parent = models.ForeignKey('self', models.CASCADE)

            class Meta:
                constraints = [
                    models.CheckConstraint(
                        name='name1', check=models.Q(
                            field1__lt=models.F('parent__field1') + models.F('parent__field2')
                        )
                    ),
                    models.CheckConstraint(
                        name='name2', check=models.Q(name=Lower('parent__name'))
                    ),
                    models.CheckConstraint(
                        name='name3', check=models.Q(parent__field3=models.F('field1'))
                    ),
                ]

        joined_fields = ['parent__field1', 'parent__field2', 'parent__field3', 'parent__name']
        errors = Model.check(databases=self.databases)
        expected_errors = [
            Error(
                "'constraints' refers to the joined field '%s'." % field_name,
                obj=Model,
                id='models.E041',
            ) for field_name in joined_fields
        ]
        self.assertCountEqual(errors, expected_errors)

    @skipUnlessDBFeature('supports_table_check_constraints')
    def test_check_constraint_pointing_to_joined_fields_complex_check(self):
        class Model(models.Model):
            name = models.PositiveSmallIntegerField()
            field1 = models.PositiveSmallIntegerField()
            field2 = models.PositiveSmallIntegerField()
            parent = models.ForeignKey('self', models.CASCADE)

            class Meta:
                constraints = [
                    models.CheckConstraint(
                        name='name',
                        check=models.Q(
                            (
                                models.Q(name='test') &
                                models.Q(field1__lt=models.F('parent__field1'))
                            ) |
                            (
                                models.Q(name__startswith=Lower('parent__name')) &
                                models.Q(field1__gte=(
                                    models.F('parent__field1') + models.F('parent__field2')
                                ))
                            )
                        ) | (models.Q(name='test1'))
                    ),
                ]

        joined_fields = ['parent__field1', 'parent__field2', 'parent__name']
        errors = Model.check(databases=self.databases)
        expected_errors = [
            Error(
                "'constraints' refers to the joined field '%s'." % field_name,
                obj=Model,
                id='models.E041',
            ) for field_name in joined_fields
        ]
        self.assertCountEqual(errors, expected_errors)

    def test_unique_constraint_with_condition(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['age'],
                        name='unique_age_gte_100',
                        condition=models.Q(age__gte=100),
                    ),
                ]

        errors = Model.check(databases=self.databases)
        expected = [] if connection.features.supports_partial_indexes else [
            Warning(
                '%s does not support unique constraints with conditions.'
                % connection.display_name,
                hint=(
                    "A constraint won't be created. Silence this warning if "
                    "you don't care about it."
                ),
                obj=Model,
                id='models.W036',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_unique_constraint_with_condition_required_db_features(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                required_db_features = {'supports_partial_indexes'}
                constraints = [
                    models.UniqueConstraint(
                        fields=['age'],
                        name='unique_age_gte_100',
                        condition=models.Q(age__gte=100),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    def test_unique_constraint_condition_pointing_to_missing_field(self):
        class Model(models.Model):
            age = models.SmallIntegerField()

            class Meta:
                required_db_features = {'supports_partial_indexes'}
                constraints = [
                    models.UniqueConstraint(
                        name='name',
                        fields=['age'],
                        condition=models.Q(missing_field=2),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the nonexistent field "
                "'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ] if connection.features.supports_partial_indexes else [])

    def test_unique_constraint_condition_pointing_to_joined_fields(self):
        class Model(models.Model):
            age = models.SmallIntegerField()
            parent = models.ForeignKey('self', models.CASCADE)

            class Meta:
                required_db_features = {'supports_partial_indexes'}
                constraints = [
                    models.UniqueConstraint(
                        name='name',
                        fields=['age'],
                        condition=models.Q(parent__age__lt=2),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the joined field 'parent__age__lt'.",
                obj=Model,
                id='models.E041',
            )
        ] if connection.features.supports_partial_indexes else [])

    def test_unique_constraint_pointing_to_reverse_o2o(self):
        class Model(models.Model):
            parent = models.OneToOneField('self', models.CASCADE)

            class Meta:
                required_db_features = {'supports_partial_indexes'}
                constraints = [
                    models.UniqueConstraint(
                        fields=['parent'],
                        name='name',
                        condition=models.Q(model__isnull=True),
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the nonexistent field 'model'.",
                obj=Model,
                id='models.E012',
            ),
        ] if connection.features.supports_partial_indexes else [])

    def test_deferrable_unique_constraint(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['age'],
                        name='unique_age_deferrable',
                        deferrable=models.Deferrable.DEFERRED,
                    ),
                ]

        errors = Model.check(databases=self.databases)
        expected = [] if connection.features.supports_deferrable_unique_constraints else [
            Warning(
                '%s does not support deferrable unique constraints.'
                % connection.display_name,
                hint=(
                    "A constraint won't be created. Silence this warning if "
                    "you don't care about it."
                ),
                obj=Model,
                id='models.W038',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_deferrable_unique_constraint_required_db_features(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                required_db_features = {'supports_deferrable_unique_constraints'}
                constraints = [
                    models.UniqueConstraint(
                        fields=['age'],
                        name='unique_age_deferrable',
                        deferrable=models.Deferrable.IMMEDIATE,
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    def test_unique_constraint_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                constraints = [models.UniqueConstraint(fields=['missing_field'], name='name')]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the nonexistent field "
                "'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    def test_unique_constraint_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                constraints = [models.UniqueConstraint(fields=['m2m'], name='name')]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'constraints'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    def test_unique_constraint_pointing_to_non_local_field(self):
        class Parent(models.Model):
            field1 = models.IntegerField()

        class Child(Parent):
            field2 = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(fields=['field2', 'field1'], name='name'),
                ]

        self.assertEqual(Child.check(databases=self.databases), [
            Error(
                "'constraints' refers to field 'field1' which is not local to "
                "model 'Child'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Child,
                id='models.E016',
            ),
        ])

    def test_unique_constraint_pointing_to_fk(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk_1 = models.ForeignKey(Target, models.CASCADE, related_name='target_1')
            fk_2 = models.ForeignKey(Target, models.CASCADE, related_name='target_2')

            class Meta:
                constraints = [
                    models.UniqueConstraint(fields=['fk_1_id', 'fk_2'], name='name'),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    def test_unique_constraint_with_include(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['age'],
                        name='unique_age_include_id',
                        include=['id'],
                    ),
                ]

        errors = Model.check(databases=self.databases)
        expected = [] if connection.features.supports_covering_indexes else [
            Warning(
                '%s does not support unique constraints with non-key columns.'
                % connection.display_name,
                hint=(
                    "A constraint won't be created. Silence this warning if "
                    "you don't care about it."
                ),
                obj=Model,
                id='models.W039',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_unique_constraint_with_include_required_db_features(self):
        class Model(models.Model):
            age = models.IntegerField()

            class Meta:
                required_db_features = {'supports_covering_indexes'}
                constraints = [
                    models.UniqueConstraint(
                        fields=['age'],
                        name='unique_age_include_id',
                        include=['id'],
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_unique_constraint_include_pointing_to_missing_field(self):
        class Model(models.Model):
            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['id'],
                        include=['missing_field'],
                        name='name',
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to the nonexistent field "
                "'missing_field'.",
                obj=Model,
                id='models.E012',
            ),
        ])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_unique_constraint_include_pointing_to_m2m_field(self):
        class Model(models.Model):
            m2m = models.ManyToManyField('self')

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['id'],
                        include=['m2m'],
                        name='name',
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [
            Error(
                "'constraints' refers to a ManyToManyField 'm2m', but "
                "ManyToManyFields are not permitted in 'constraints'.",
                obj=Model,
                id='models.E013',
            ),
        ])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_unique_constraint_include_pointing_to_non_local_field(self):
        class Parent(models.Model):
            field1 = models.IntegerField()

        class Child(Parent):
            field2 = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['field2'],
                        include=['field1'],
                        name='name',
                    ),
                ]

        self.assertEqual(Child.check(databases=self.databases), [
            Error(
                "'constraints' refers to field 'field1' which is not local to "
                "model 'Child'.",
                hint='This issue may be caused by multi-table inheritance.',
                obj=Child,
                id='models.E016',
            ),
        ])

    @skipUnlessDBFeature('supports_covering_indexes')
    def test_unique_constraint_include_pointing_to_fk(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            fk_1 = models.ForeignKey(Target, models.CASCADE, related_name='target_1')
            fk_2 = models.ForeignKey(Target, models.CASCADE, related_name='target_2')

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['id'],
                        include=['fk_1_id', 'fk_2'],
                        name='name',
                    ),
                ]

        self.assertEqual(Model.check(databases=self.databases), [])
