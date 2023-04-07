from unittest import mock

from django.core.checks import Error
from django.core.checks import Warning as DjangoWarning
from django.db import connection, models
from django.test.testcases import SimpleTestCase
from django.test.utils import isolate_apps, modify_settings, override_settings


@isolate_apps("invalid_models_tests")
class RelativeFieldTests(SimpleTestCase):
    def test_valid_foreign_key_without_accessor(self):
        class Target(models.Model):
            # There would be a clash if Model.field installed an accessor.
            model = models.IntegerField()

        class Model(models.Model):
            field = models.ForeignKey(Target, models.CASCADE, related_name="+")

        field = Model._meta.get_field("field")
        self.assertEqual(field.check(), [])

    def test_foreign_key_to_missing_model(self):
        # Model names are resolved when a model is being created, so we cannot
        # test relative fields in isolation and we need to attach them to a
        # model.
        class Model(models.Model):
            foreign_key = models.ForeignKey("Rel1", models.CASCADE)

        field = Model._meta.get_field("foreign_key")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "Field defines a relation with model 'Rel1', "
                    "which is either not installed, or is abstract.",
                    obj=field,
                    id="fields.E300",
                ),
            ],
        )

    @isolate_apps("invalid_models_tests")
    def test_foreign_key_to_isolate_apps_model(self):
        """
        #25723 - Referenced model registration lookup should be run against the
        field's model registry.
        """

        class OtherModel(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey("OtherModel", models.CASCADE)

        field = Model._meta.get_field("foreign_key")
        self.assertEqual(field.check(from_model=Model), [])

    def test_one_to_one_with_useless_options(self):
        class OtherModel(models.Model):
            pass

        class Model(models.Model):
            one_to_one = models.OneToOneField(OtherModel, models.CASCADE, unique=True)

        field = Model._meta.get_field("one_to_one")
        self.assertEqual(
            Model.check(),
            [
                DjangoWarning(
                    "unique has no effect on OneToOneField.",
                    obj=field,
                    id="fields.W347",
                ),
            ],
        )

    def test_many_to_many_to_missing_model(self):
        class Model(models.Model):
            m2m = models.ManyToManyField("Rel2")

        field = Model._meta.get_field("m2m")
        self.assertEqual(
            field.check(from_model=Model),
            [
                Error(
                    "Field defines a relation with model 'Rel2', "
                    "which is either not installed, or is abstract.",
                    obj=field,
                    id="fields.E300",
                ),
            ],
        )

    @isolate_apps("invalid_models_tests")
    def test_many_to_many_to_isolate_apps_model(self):
        """
        #25723 - Referenced model registration lookup should be run against the
        field's model registry.
        """

        class OtherModel(models.Model):
            pass

        class Model(models.Model):
            m2m = models.ManyToManyField("OtherModel")

        field = Model._meta.get_field("m2m")
        self.assertEqual(field.check(from_model=Model), [])

    def test_many_to_many_with_useless_options(self):
        class Model(models.Model):
            name = models.CharField(max_length=20)

        class ModelM2M(models.Model):
            m2m = models.ManyToManyField(
                Model, null=True, validators=[lambda x: x], db_comment="Column comment"
            )

        field = ModelM2M._meta.get_field("m2m")
        self.assertEqual(
            ModelM2M.check(),
            [
                DjangoWarning(
                    "null has no effect on ManyToManyField.",
                    obj=field,
                    id="fields.W340",
                ),
                DjangoWarning(
                    "ManyToManyField does not support validators.",
                    obj=field,
                    id="fields.W341",
                ),
                DjangoWarning(
                    "db_comment has no effect on ManyToManyField.",
                    obj=field,
                    id="fields.W346",
                ),
            ],
        )

    def test_many_to_many_with_useless_related_name(self):
        class ModelM2M(models.Model):
            m2m = models.ManyToManyField("self", related_name="children")

        field = ModelM2M._meta.get_field("m2m")
        self.assertEqual(
            ModelM2M.check(),
            [
                DjangoWarning(
                    "related_name has no effect on ManyToManyField with "
                    'a symmetrical relationship, e.g. to "self".',
                    obj=field,
                    id="fields.W345",
                ),
            ],
        )

    def test_ambiguous_relationship_model_from(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            field = models.ManyToManyField("Person", through="AmbiguousRelationship")

        class AmbiguousRelationship(models.Model):
            person = models.ForeignKey(Person, models.CASCADE)
            first_group = models.ForeignKey(Group, models.CASCADE, related_name="first")
            second_group = models.ForeignKey(
                Group, models.CASCADE, related_name="second"
            )

        field = Group._meta.get_field("field")
        self.assertEqual(
            field.check(from_model=Group),
            [
                Error(
                    "The model is used as an intermediate model by "
                    "'invalid_models_tests.Group.field', but it has more than one "
                    "foreign key from 'Group', which is ambiguous. You must "
                    "specify which foreign key Django should use via the "
                    "through_fields keyword argument.",
                    hint=(
                        "If you want to create a recursive relationship, use "
                        'ManyToManyField("self", through="AmbiguousRelationship").'
                    ),
                    obj=field,
                    id="fields.E334",
                ),
            ],
        )

    def test_ambiguous_relationship_model_to(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            field = models.ManyToManyField(
                "Person", through="AmbiguousRelationship", related_name="tertiary"
            )

        class AmbiguousRelationship(models.Model):
            # Too much foreign keys to Person.
            first_person = models.ForeignKey(
                Person, models.CASCADE, related_name="first"
            )
            second_person = models.ForeignKey(
                Person, models.CASCADE, related_name="second"
            )
            second_model = models.ForeignKey(Group, models.CASCADE)

        field = Group._meta.get_field("field")
        self.assertEqual(
            field.check(from_model=Group),
            [
                Error(
                    "The model is used as an intermediate model by "
                    "'invalid_models_tests.Group.field', but it has more than one "
                    "foreign key to 'Person', which is ambiguous. You must specify "
                    "which foreign key Django should use via the through_fields "
                    "keyword argument.",
                    hint=(
                        "If you want to create a recursive relationship, use "
                        'ManyToManyField("self", through="AmbiguousRelationship").'
                    ),
                    obj=field,
                    id="fields.E335",
                ),
            ],
        )

    def test_relationship_model_with_foreign_key_to_wrong_model(self):
        class WrongModel(models.Model):
            pass

        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField("Person", through="InvalidRelationship")

        class InvalidRelationship(models.Model):
            person = models.ForeignKey(Person, models.CASCADE)
            wrong_foreign_key = models.ForeignKey(WrongModel, models.CASCADE)
            # The last foreign key should point to Group model.

        field = Group._meta.get_field("members")
        self.assertEqual(
            field.check(from_model=Group),
            [
                Error(
                    "The model is used as an intermediate model by "
                    "'invalid_models_tests.Group.members', but it does not "
                    "have a foreign key to 'Group' or 'Person'.",
                    obj=InvalidRelationship,
                    id="fields.E336",
                ),
            ],
        )

    def test_relationship_model_missing_foreign_key(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField("Person", through="InvalidRelationship")

        class InvalidRelationship(models.Model):
            group = models.ForeignKey(Group, models.CASCADE)
            # No foreign key to Person

        field = Group._meta.get_field("members")
        self.assertEqual(
            field.check(from_model=Group),
            [
                Error(
                    "The model is used as an intermediate model by "
                    "'invalid_models_tests.Group.members', but it does not have "
                    "a foreign key to 'Group' or 'Person'.",
                    obj=InvalidRelationship,
                    id="fields.E336",
                ),
            ],
        )

    def test_missing_relationship_model(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField("Person", through="MissingM2MModel")

        field = Group._meta.get_field("members")
        self.assertEqual(
            field.check(from_model=Group),
            [
                Error(
                    "Field specifies a many-to-many relation through model "
                    "'MissingM2MModel', which has not been installed.",
                    obj=field,
                    id="fields.E331",
                ),
            ],
        )

    def test_missing_relationship_model_on_model_check(self):
        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField("Person", through="MissingM2MModel")

        self.assertEqual(
            Group.check(),
            [
                Error(
                    "Field specifies a many-to-many relation through model "
                    "'MissingM2MModel', which has not been installed.",
                    obj=Group._meta.get_field("members"),
                    id="fields.E331",
                ),
            ],
        )

    @isolate_apps("invalid_models_tests")
    def test_many_to_many_through_isolate_apps_model(self):
        """
        #25723 - Through model registration lookup should be run against the
        field's model registry.
        """

        class GroupMember(models.Model):
            person = models.ForeignKey("Person", models.CASCADE)
            group = models.ForeignKey("Group", models.CASCADE)

        class Person(models.Model):
            pass

        class Group(models.Model):
            members = models.ManyToManyField("Person", through="GroupMember")

        field = Group._meta.get_field("members")
        self.assertEqual(field.check(from_model=Group), [])

    def test_too_many_foreign_keys_in_self_referential_model(self):
        class Person(models.Model):
            friends = models.ManyToManyField(
                "self", through="InvalidRelationship", symmetrical=False
            )

        class InvalidRelationship(models.Model):
            first = models.ForeignKey(
                Person, models.CASCADE, related_name="rel_from_set_2"
            )
            second = models.ForeignKey(
                Person, models.CASCADE, related_name="rel_to_set_2"
            )
            third = models.ForeignKey(
                Person, models.CASCADE, related_name="too_many_by_far"
            )

        field = Person._meta.get_field("friends")
        self.assertEqual(
            field.check(from_model=Person),
            [
                Error(
                    "The model is used as an intermediate model by "
                    "'invalid_models_tests.Person.friends', but it has more than two "
                    "foreign keys to 'Person', which is ambiguous. You must specify "
                    "which two foreign keys Django should use via the through_fields "
                    "keyword argument.",
                    hint=(
                        "Use through_fields to specify which two foreign keys Django "
                        "should use."
                    ),
                    obj=InvalidRelationship,
                    id="fields.E333",
                ),
            ],
        )

    def test_foreign_key_to_abstract_model(self):
        class AbstractModel(models.Model):
            class Meta:
                abstract = True

        class Model(models.Model):
            rel_string_foreign_key = models.ForeignKey("AbstractModel", models.CASCADE)
            rel_class_foreign_key = models.ForeignKey(AbstractModel, models.CASCADE)

        fields = [
            Model._meta.get_field("rel_string_foreign_key"),
            Model._meta.get_field("rel_class_foreign_key"),
        ]
        expected_error = Error(
            "Field defines a relation with model 'AbstractModel', "
            "which is either not installed, or is abstract.",
            id="fields.E300",
        )
        for field in fields:
            expected_error.obj = field
            self.assertEqual(field.check(), [expected_error])

    def test_m2m_to_abstract_model(self):
        class AbstractModel(models.Model):
            class Meta:
                abstract = True

        class Model(models.Model):
            rel_string_m2m = models.ManyToManyField("AbstractModel")
            rel_class_m2m = models.ManyToManyField(AbstractModel)

        fields = [
            Model._meta.get_field("rel_string_m2m"),
            Model._meta.get_field("rel_class_m2m"),
        ]
        expected_error = Error(
            "Field defines a relation with model 'AbstractModel', "
            "which is either not installed, or is abstract.",
            id="fields.E300",
        )
        for field in fields:
            expected_error.obj = field
            self.assertEqual(field.check(from_model=Model), [expected_error])

    def test_unique_m2m(self):
        class Person(models.Model):
            name = models.CharField(max_length=5)

        class Group(models.Model):
            members = models.ManyToManyField("Person", unique=True)

        field = Group._meta.get_field("members")
        self.assertEqual(
            field.check(from_model=Group),
            [
                Error(
                    "ManyToManyFields cannot be unique.",
                    obj=field,
                    id="fields.E330",
                ),
            ],
        )

    def test_foreign_key_to_non_unique_field(self):
        class Target(models.Model):
            bad = models.IntegerField()  # No unique=True

        class Model(models.Model):
            foreign_key = models.ForeignKey("Target", models.CASCADE, to_field="bad")

        field = Model._meta.get_field("foreign_key")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "'Target.bad' must be unique because it is referenced by a foreign "
                    "key.",
                    hint=(
                        "Add unique=True to this field or add a UniqueConstraint "
                        "(without condition) in the model Meta.constraints."
                    ),
                    obj=field,
                    id="fields.E311",
                ),
            ],
        )

    def test_foreign_key_to_non_unique_field_under_explicit_model(self):
        class Target(models.Model):
            bad = models.IntegerField()

        class Model(models.Model):
            field = models.ForeignKey(Target, models.CASCADE, to_field="bad")

        field = Model._meta.get_field("field")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "'Target.bad' must be unique because it is referenced by a foreign "
                    "key.",
                    hint=(
                        "Add unique=True to this field or add a UniqueConstraint "
                        "(without condition) in the model Meta.constraints."
                    ),
                    obj=field,
                    id="fields.E311",
                ),
            ],
        )

    def test_foreign_key_to_partially_unique_field(self):
        class Target(models.Model):
            source = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=["source"],
                        name="tfktpuf_partial_unique",
                        condition=models.Q(pk__gt=2),
                    ),
                ]

        class Model(models.Model):
            field = models.ForeignKey(Target, models.CASCADE, to_field="source")

        field = Model._meta.get_field("field")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "'Target.source' must be unique because it is referenced by a "
                    "foreign key.",
                    hint=(
                        "Add unique=True to this field or add a UniqueConstraint "
                        "(without condition) in the model Meta.constraints."
                    ),
                    obj=field,
                    id="fields.E311",
                ),
            ],
        )

    def test_foreign_key_to_unique_field_with_meta_constraint(self):
        class Target(models.Model):
            source = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=["source"],
                        name="tfktufwmc_unique",
                    ),
                ]

        class Model(models.Model):
            field = models.ForeignKey(Target, models.CASCADE, to_field="source")

        field = Model._meta.get_field("field")
        self.assertEqual(field.check(), [])

    def test_foreign_object_to_non_unique_fields(self):
        class Person(models.Model):
            # Note that both fields are not unique.
            country_id = models.IntegerField()
            city_id = models.IntegerField()

        class MMembership(models.Model):
            person_country_id = models.IntegerField()
            person_city_id = models.IntegerField()

            person = models.ForeignObject(
                Person,
                on_delete=models.CASCADE,
                from_fields=["person_country_id", "person_city_id"],
                to_fields=["country_id", "city_id"],
            )

        field = MMembership._meta.get_field("person")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "No subset of the fields 'country_id', 'city_id' on model 'Person' "
                    "is unique.",
                    hint=(
                        "Mark a single field as unique=True or add a set of "
                        "fields to a unique constraint (via unique_together or a "
                        "UniqueConstraint (without condition) in the model "
                        "Meta.constraints)."
                    ),
                    obj=field,
                    id="fields.E310",
                )
            ],
        )

    def test_foreign_object_to_partially_unique_field(self):
        class Person(models.Model):
            country_id = models.IntegerField()
            city_id = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=["country_id", "city_id"],
                        name="tfotpuf_partial_unique",
                        condition=models.Q(pk__gt=2),
                    ),
                ]

        class MMembership(models.Model):
            person_country_id = models.IntegerField()
            person_city_id = models.IntegerField()
            person = models.ForeignObject(
                Person,
                on_delete=models.CASCADE,
                from_fields=["person_country_id", "person_city_id"],
                to_fields=["country_id", "city_id"],
            )

        field = MMembership._meta.get_field("person")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "No subset of the fields 'country_id', 'city_id' on model "
                    "'Person' is unique.",
                    hint=(
                        "Mark a single field as unique=True or add a set of "
                        "fields to a unique constraint (via unique_together or a "
                        "UniqueConstraint (without condition) in the model "
                        "Meta.constraints)."
                    ),
                    obj=field,
                    id="fields.E310",
                ),
            ],
        )

    def test_foreign_object_to_unique_field_with_meta_constraint(self):
        class Person(models.Model):
            country_id = models.IntegerField()
            city_id = models.IntegerField()

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=["country_id", "city_id"],
                        name="tfotpuf_unique",
                    ),
                ]

        class MMembership(models.Model):
            person_country_id = models.IntegerField()
            person_city_id = models.IntegerField()
            person = models.ForeignObject(
                Person,
                on_delete=models.CASCADE,
                from_fields=["person_country_id", "person_city_id"],
                to_fields=["country_id", "city_id"],
            )

        field = MMembership._meta.get_field("person")
        self.assertEqual(field.check(), [])

    def test_on_delete_set_null_on_non_nullable_field(self):
        class Person(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey("Person", models.SET_NULL)

        field = Model._meta.get_field("foreign_key")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "Field specifies on_delete=SET_NULL, but cannot be null.",
                    hint=(
                        "Set null=True argument on the field, or change the on_delete "
                        "rule."
                    ),
                    obj=field,
                    id="fields.E320",
                ),
            ],
        )

    def test_on_delete_set_default_without_default_value(self):
        class Person(models.Model):
            pass

        class Model(models.Model):
            foreign_key = models.ForeignKey("Person", models.SET_DEFAULT)

        field = Model._meta.get_field("foreign_key")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "Field specifies on_delete=SET_DEFAULT, but has no default value.",
                    hint="Set a default value, or change the on_delete rule.",
                    obj=field,
                    id="fields.E321",
                ),
            ],
        )

    def test_nullable_primary_key(self):
        class Model(models.Model):
            field = models.IntegerField(primary_key=True, null=True)

        field = Model._meta.get_field("field")
        with mock.patch.object(
            connection.features, "interprets_empty_strings_as_nulls", False
        ):
            results = field.check()
        self.assertEqual(
            results,
            [
                Error(
                    "Primary keys must not have null=True.",
                    hint=(
                        "Set null=False on the field, or remove primary_key=True "
                        "argument."
                    ),
                    obj=field,
                    id="fields.E007",
                ),
            ],
        )

    def test_not_swapped_model(self):
        class SwappableModel(models.Model):
            # A model that can be, but isn't swapped out. References to this
            # model should *not* raise any validation error.
            class Meta:
                swappable = "TEST_SWAPPABLE_MODEL"

        class Model(models.Model):
            explicit_fk = models.ForeignKey(
                SwappableModel,
                models.CASCADE,
                related_name="explicit_fk",
            )
            implicit_fk = models.ForeignKey(
                "invalid_models_tests.SwappableModel",
                models.CASCADE,
                related_name="implicit_fk",
            )
            explicit_m2m = models.ManyToManyField(
                SwappableModel, related_name="explicit_m2m"
            )
            implicit_m2m = models.ManyToManyField(
                "invalid_models_tests.SwappableModel",
                related_name="implicit_m2m",
            )

        explicit_fk = Model._meta.get_field("explicit_fk")
        self.assertEqual(explicit_fk.check(), [])

        implicit_fk = Model._meta.get_field("implicit_fk")
        self.assertEqual(implicit_fk.check(), [])

        explicit_m2m = Model._meta.get_field("explicit_m2m")
        self.assertEqual(explicit_m2m.check(from_model=Model), [])

        implicit_m2m = Model._meta.get_field("implicit_m2m")
        self.assertEqual(implicit_m2m.check(from_model=Model), [])

    @override_settings(TEST_SWAPPED_MODEL="invalid_models_tests.Replacement")
    def test_referencing_to_swapped_model(self):
        class Replacement(models.Model):
            pass

        class SwappedModel(models.Model):
            class Meta:
                swappable = "TEST_SWAPPED_MODEL"

        class Model(models.Model):
            explicit_fk = models.ForeignKey(
                SwappedModel,
                models.CASCADE,
                related_name="explicit_fk",
            )
            implicit_fk = models.ForeignKey(
                "invalid_models_tests.SwappedModel",
                models.CASCADE,
                related_name="implicit_fk",
            )
            explicit_m2m = models.ManyToManyField(
                SwappedModel, related_name="explicit_m2m"
            )
            implicit_m2m = models.ManyToManyField(
                "invalid_models_tests.SwappedModel",
                related_name="implicit_m2m",
            )

        fields = [
            Model._meta.get_field("explicit_fk"),
            Model._meta.get_field("implicit_fk"),
            Model._meta.get_field("explicit_m2m"),
            Model._meta.get_field("implicit_m2m"),
        ]

        expected_error = Error(
            (
                "Field defines a relation with the model "
                "'invalid_models_tests.SwappedModel', which has been swapped out."
            ),
            hint="Update the relation to point at 'settings.TEST_SWAPPED_MODEL'.",
            id="fields.E301",
        )

        for field in fields:
            expected_error.obj = field
            self.assertEqual(field.check(from_model=Model), [expected_error])

    def test_related_field_has_invalid_related_name(self):
        digit = 0
        illegal_non_alphanumeric = "!"
        whitespace = "\t"

        invalid_related_names = [
            "%s_begins_with_digit" % digit,
            "%s_begins_with_illegal_non_alphanumeric" % illegal_non_alphanumeric,
            "%s_begins_with_whitespace" % whitespace,
            "contains_%s_illegal_non_alphanumeric" % illegal_non_alphanumeric,
            "contains_%s_whitespace" % whitespace,
            "ends_with_with_illegal_non_alphanumeric_%s" % illegal_non_alphanumeric,
            "ends_with_whitespace_%s" % whitespace,
            "with",  # a Python keyword
            "related_name\n",
            "",
            "，",  # non-ASCII
        ]

        class Parent(models.Model):
            pass

        for invalid_related_name in invalid_related_names:
            Child = type(
                "Child%s" % invalid_related_name,
                (models.Model,),
                {
                    "parent": models.ForeignKey(
                        "Parent", models.CASCADE, related_name=invalid_related_name
                    ),
                    "__module__": Parent.__module__,
                },
            )

            field = Child._meta.get_field("parent")
            self.assertEqual(
                Child.check(),
                [
                    Error(
                        "The name '%s' is invalid related_name for field Child%s.parent"
                        % (invalid_related_name, invalid_related_name),
                        hint=(
                            "Related name must be a valid Python identifier or end "
                            "with a '+'"
                        ),
                        obj=field,
                        id="fields.E306",
                    ),
                ],
            )

    def test_related_field_has_valid_related_name(self):
        lowercase = "a"
        uppercase = "A"
        digit = 0

        related_names = [
            "%s_starts_with_lowercase" % lowercase,
            "%s_tarts_with_uppercase" % uppercase,
            "_starts_with_underscore",
            "contains_%s_digit" % digit,
            "ends_with_plus+",
            "_+",
            "+",
            "試",
            "試驗+",
        ]

        class Parent(models.Model):
            pass

        for related_name in related_names:
            Child = type(
                "Child%s" % related_name,
                (models.Model,),
                {
                    "parent": models.ForeignKey(
                        "Parent", models.CASCADE, related_name=related_name
                    ),
                    "__module__": Parent.__module__,
                },
            )
            self.assertEqual(Child.check(), [])

    def test_to_fields_exist(self):
        class Parent(models.Model):
            pass

        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            parent = models.ForeignObject(
                Parent,
                on_delete=models.SET_NULL,
                from_fields=("a", "b"),
                to_fields=("a", "b"),
            )

        field = Child._meta.get_field("parent")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "The to_field 'a' doesn't exist on the related model "
                    "'invalid_models_tests.Parent'.",
                    obj=field,
                    id="fields.E312",
                ),
                Error(
                    "The to_field 'b' doesn't exist on the related model "
                    "'invalid_models_tests.Parent'.",
                    obj=field,
                    id="fields.E312",
                ),
            ],
        )

    def test_to_fields_not_checked_if_related_model_doesnt_exist(self):
        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            parent = models.ForeignObject(
                "invalid_models_tests.Parent",
                on_delete=models.SET_NULL,
                from_fields=("a", "b"),
                to_fields=("a", "b"),
            )

        field = Child._meta.get_field("parent")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "Field defines a relation with model "
                    "'invalid_models_tests.Parent', which is either not installed, or "
                    "is abstract.",
                    id="fields.E300",
                    obj=field,
                ),
            ],
        )

    def test_invalid_related_query_name(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            first = models.ForeignKey(
                Target, models.CASCADE, related_name="contains__double"
            )
            second = models.ForeignKey(
                Target, models.CASCADE, related_query_name="ends_underscore_"
            )

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse query name 'contains__double' must not contain '__'.",
                    hint=(
                        "Add or change a related_name or related_query_name "
                        "argument for this field."
                    ),
                    obj=Model._meta.get_field("first"),
                    id="fields.E309",
                ),
                Error(
                    "Reverse query name 'ends_underscore_' must not end with an "
                    "underscore.",
                    hint=(
                        "Add or change a related_name or related_query_name "
                        "argument for this field."
                    ),
                    obj=Model._meta.get_field("second"),
                    id="fields.E308",
                ),
            ],
        )


@isolate_apps("invalid_models_tests")
class AccessorClashTests(SimpleTestCase):
    def test_fk_to_integer(self):
        self._test_accessor_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey("Target", models.CASCADE),
        )

    def test_fk_to_fk(self):
        self._test_accessor_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ForeignKey("Target", models.CASCADE),
        )

    def test_fk_to_m2m(self):
        self._test_accessor_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ForeignKey("Target", models.CASCADE),
        )

    def test_m2m_to_integer(self):
        self._test_accessor_clash(
            target=models.IntegerField(), relative=models.ManyToManyField("Target")
        )

    def test_m2m_to_fk(self):
        self._test_accessor_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ManyToManyField("Target"),
        )

    def test_m2m_to_m2m(self):
        self._test_accessor_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ManyToManyField("Target"),
        )

    def _test_accessor_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            model_set = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Target.model_set' for "
                    "'invalid_models_tests.Model.rel' clashes with field name "
                    "'invalid_models_tests.Target.model_set'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.model_set', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.rel'."
                    ),
                    obj=Model._meta.get_field("rel"),
                    id="fields.E302",
                ),
            ],
        )

    def test_clash_between_accessors(self):
        class Target(models.Model):
            pass

        class Model(models.Model):
            foreign = models.ForeignKey(Target, models.CASCADE)
            m2m = models.ManyToManyField(Target)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Target.model_set' for "
                    "'invalid_models_tests.Model.foreign' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.m2m'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.foreign' or "
                        "'invalid_models_tests.Model.m2m'."
                    ),
                    obj=Model._meta.get_field("foreign"),
                    id="fields.E304",
                ),
                Error(
                    "Reverse accessor 'Target.model_set' for "
                    "'invalid_models_tests.Model.m2m' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.foreign'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.m2m' or "
                        "'invalid_models_tests.Model.foreign'."
                    ),
                    obj=Model._meta.get_field("m2m"),
                    id="fields.E304",
                ),
            ],
        )

    def test_m2m_to_m2m_with_inheritance(self):
        """Ref #22047."""

        class Target(models.Model):
            pass

        class Model(models.Model):
            children = models.ManyToManyField(
                "Child", related_name="m2m_clash", related_query_name="no_clash"
            )

        class Parent(models.Model):
            m2m_clash = models.ManyToManyField("Target")

        class Child(Parent):
            pass

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Child.m2m_clash' for "
                    "'invalid_models_tests.Model.children' clashes with field "
                    "name 'invalid_models_tests.Child.m2m_clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Child.m2m_clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.children'."
                    ),
                    obj=Model._meta.get_field("children"),
                    id="fields.E302",
                )
            ],
        )

    def test_no_clash_for_hidden_related_name(self):
        class Stub(models.Model):
            pass

        class ManyToManyRel(models.Model):
            thing1 = models.ManyToManyField(Stub, related_name="+")
            thing2 = models.ManyToManyField(Stub, related_name="+")

        class FKRel(models.Model):
            thing1 = models.ForeignKey(Stub, models.CASCADE, related_name="+")
            thing2 = models.ForeignKey(Stub, models.CASCADE, related_name="+")

        self.assertEqual(ManyToManyRel.check(), [])
        self.assertEqual(FKRel.check(), [])


@isolate_apps("invalid_models_tests")
class ReverseQueryNameClashTests(SimpleTestCase):
    def test_fk_to_integer(self):
        self._test_reverse_query_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey("Target", models.CASCADE),
        )

    def test_fk_to_fk(self):
        self._test_reverse_query_name_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ForeignKey("Target", models.CASCADE),
        )

    def test_fk_to_m2m(self):
        self._test_reverse_query_name_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ForeignKey("Target", models.CASCADE),
        )

    def test_m2m_to_integer(self):
        self._test_reverse_query_name_clash(
            target=models.IntegerField(), relative=models.ManyToManyField("Target")
        )

    def test_m2m_to_fk(self):
        self._test_reverse_query_name_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ManyToManyField("Target"),
        )

    def test_m2m_to_m2m(self):
        self._test_reverse_query_name_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ManyToManyField("Target"),
        )

    def _test_reverse_query_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            model = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.rel' "
                    "clashes with field name 'invalid_models_tests.Target.model'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.model', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.rel'."
                    ),
                    obj=Model._meta.get_field("rel"),
                    id="fields.E303",
                ),
            ],
        )

    @modify_settings(INSTALLED_APPS={"append": "basic"})
    @isolate_apps("basic", "invalid_models_tests")
    def test_no_clash_across_apps_without_accessor(self):
        class Target(models.Model):
            class Meta:
                app_label = "invalid_models_tests"

        class Model(models.Model):
            m2m = models.ManyToManyField(Target, related_name="+")

            class Meta:
                app_label = "basic"

        def _test():
            # Define model with the same name.
            class Model(models.Model):
                m2m = models.ManyToManyField(Target, related_name="+")

                class Meta:
                    app_label = "invalid_models_tests"

            self.assertEqual(Model.check(), [])

        _test()
        self.assertEqual(Model.check(), [])


@isolate_apps("invalid_models_tests")
class ExplicitRelatedNameClashTests(SimpleTestCase):
    def test_fk_to_integer(self):
        self._test_explicit_related_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey("Target", models.CASCADE, related_name="clash"),
        )

    def test_fk_to_fk(self):
        self._test_explicit_related_name_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ForeignKey("Target", models.CASCADE, related_name="clash"),
        )

    def test_fk_to_m2m(self):
        self._test_explicit_related_name_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ForeignKey("Target", models.CASCADE, related_name="clash"),
        )

    def test_m2m_to_integer(self):
        self._test_explicit_related_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField("Target", related_name="clash"),
        )

    def test_m2m_to_fk(self):
        self._test_explicit_related_name_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ManyToManyField("Target", related_name="clash"),
        )

    def test_m2m_to_m2m(self):
        self._test_explicit_related_name_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ManyToManyField("Target", related_name="clash"),
        )

    def _test_explicit_related_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            clash = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Target.clash' for "
                    "'invalid_models_tests.Model.rel' clashes with field name "
                    "'invalid_models_tests.Target.clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.rel'."
                    ),
                    obj=Model._meta.get_field("rel"),
                    id="fields.E302",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.rel' "
                    "clashes with field name 'invalid_models_tests.Target.clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.rel'."
                    ),
                    obj=Model._meta.get_field("rel"),
                    id="fields.E303",
                ),
            ],
        )


@isolate_apps("invalid_models_tests")
class ExplicitRelatedQueryNameClashTests(SimpleTestCase):
    def test_fk_to_integer(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.IntegerField(),
            relative=models.ForeignKey(
                "Target",
                models.CASCADE,
                related_name=related_name,
                related_query_name="clash",
            ),
        )

    def test_hidden_fk_to_integer(self, related_name=None):
        self.test_fk_to_integer(related_name="+")

    def test_fk_to_fk(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ForeignKey(
                "Target",
                models.CASCADE,
                related_name=related_name,
                related_query_name="clash",
            ),
        )

    def test_hidden_fk_to_fk(self):
        self.test_fk_to_fk(related_name="+")

    def test_fk_to_m2m(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ForeignKey(
                "Target",
                models.CASCADE,
                related_name=related_name,
                related_query_name="clash",
            ),
        )

    def test_hidden_fk_to_m2m(self):
        self.test_fk_to_m2m(related_name="+")

    def test_m2m_to_integer(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.IntegerField(),
            relative=models.ManyToManyField(
                "Target", related_name=related_name, related_query_name="clash"
            ),
        )

    def test_hidden_m2m_to_integer(self):
        self.test_m2m_to_integer(related_name="+")

    def test_m2m_to_fk(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ForeignKey("Another", models.CASCADE),
            relative=models.ManyToManyField(
                "Target", related_name=related_name, related_query_name="clash"
            ),
        )

    def test_hidden_m2m_to_fk(self):
        self.test_m2m_to_fk(related_name="+")

    def test_m2m_to_m2m(self, related_name=None):
        self._test_explicit_related_query_name_clash(
            target=models.ManyToManyField("Another"),
            relative=models.ManyToManyField(
                "Target",
                related_name=related_name,
                related_query_name="clash",
            ),
        )

    def test_hidden_m2m_to_m2m(self):
        self.test_m2m_to_m2m(related_name="+")

    def _test_explicit_related_query_name_clash(self, target, relative):
        class Another(models.Model):
            pass

        class Target(models.Model):
            clash = target

        class Model(models.Model):
            rel = relative

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.rel' "
                    "clashes with field name 'invalid_models_tests.Target.clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.rel'."
                    ),
                    obj=Model._meta.get_field("rel"),
                    id="fields.E303",
                ),
            ],
        )


@isolate_apps("invalid_models_tests")
class SelfReferentialM2MClashTests(SimpleTestCase):
    def test_clash_between_accessors(self):
        class Model(models.Model):
            first_m2m = models.ManyToManyField("self", symmetrical=False)
            second_m2m = models.ManyToManyField("self", symmetrical=False)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Model.model_set' for "
                    "'invalid_models_tests.Model.first_m2m' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.second_m2m'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.first_m2m' or "
                        "'invalid_models_tests.Model.second_m2m'."
                    ),
                    obj=Model._meta.get_field("first_m2m"),
                    id="fields.E304",
                ),
                Error(
                    "Reverse accessor 'Model.model_set' for "
                    "'invalid_models_tests.Model.second_m2m' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.first_m2m'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.second_m2m' or "
                        "'invalid_models_tests.Model.first_m2m'."
                    ),
                    obj=Model._meta.get_field("second_m2m"),
                    id="fields.E304",
                ),
            ],
        )

    def test_accessor_clash(self):
        class Model(models.Model):
            model_set = models.ManyToManyField("self", symmetrical=False)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Model.model_set' for "
                    "'invalid_models_tests.Model.model_set' clashes with field "
                    "name 'invalid_models_tests.Model.model_set'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.model_set', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.model_set'."
                    ),
                    obj=Model._meta.get_field("model_set"),
                    id="fields.E302",
                ),
            ],
        )

    def test_reverse_query_name_clash(self):
        class Model(models.Model):
            model = models.ManyToManyField("self", symmetrical=False)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.model' "
                    "clashes with field name 'invalid_models_tests.Model.model'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.model', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.model'."
                    ),
                    obj=Model._meta.get_field("model"),
                    id="fields.E303",
                ),
            ],
        )

    def test_clash_under_explicit_related_name(self):
        class Model(models.Model):
            clash = models.IntegerField()
            m2m = models.ManyToManyField(
                "self", symmetrical=False, related_name="clash"
            )

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Model.clash' for "
                    "'invalid_models_tests.Model.m2m' clashes with field name "
                    "'invalid_models_tests.Model.clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.m2m'."
                    ),
                    obj=Model._meta.get_field("m2m"),
                    id="fields.E302",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.m2m' "
                    "clashes with field name 'invalid_models_tests.Model.clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.m2m'."
                    ),
                    obj=Model._meta.get_field("m2m"),
                    id="fields.E303",
                ),
            ],
        )

    def test_valid_model(self):
        class Model(models.Model):
            first = models.ManyToManyField(
                "self", symmetrical=False, related_name="first_accessor"
            )
            second = models.ManyToManyField(
                "self", symmetrical=False, related_name="second_accessor"
            )

        self.assertEqual(Model.check(), [])


@isolate_apps("invalid_models_tests")
class SelfReferentialFKClashTests(SimpleTestCase):
    def test_accessor_clash(self):
        class Model(models.Model):
            model_set = models.ForeignKey("Model", models.CASCADE)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Model.model_set' for "
                    "'invalid_models_tests.Model.model_set' clashes with field "
                    "name 'invalid_models_tests.Model.model_set'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.model_set', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.model_set'."
                    ),
                    obj=Model._meta.get_field("model_set"),
                    id="fields.E302",
                ),
            ],
        )

    def test_reverse_query_name_clash(self):
        class Model(models.Model):
            model = models.ForeignKey("Model", models.CASCADE)

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.model' "
                    "clashes with field name 'invalid_models_tests.Model.model'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.model', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.model'."
                    ),
                    obj=Model._meta.get_field("model"),
                    id="fields.E303",
                ),
            ],
        )

    def test_clash_under_explicit_related_name(self):
        class Model(models.Model):
            clash = models.CharField(max_length=10)
            foreign = models.ForeignKey("Model", models.CASCADE, related_name="clash")

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Model.clash' for "
                    "'invalid_models_tests.Model.foreign' clashes with field name "
                    "'invalid_models_tests.Model.clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.foreign'."
                    ),
                    obj=Model._meta.get_field("foreign"),
                    id="fields.E302",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.foreign' "
                    "clashes with field name 'invalid_models_tests.Model.clash'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Model.clash', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.foreign'."
                    ),
                    obj=Model._meta.get_field("foreign"),
                    id="fields.E303",
                ),
            ],
        )


@isolate_apps("invalid_models_tests")
class ComplexClashTests(SimpleTestCase):
    # New tests should not be included here, because this is a single,
    # self-contained sanity check, not a test of everything.
    def test_complex_clash(self):
        class Target(models.Model):
            tgt_safe = models.CharField(max_length=10)
            clash = models.CharField(max_length=10)
            model = models.CharField(max_length=10)

            clash1_set = models.CharField(max_length=10)

        class Model(models.Model):
            src_safe = models.CharField(max_length=10)

            foreign_1 = models.ForeignKey(Target, models.CASCADE, related_name="id")
            foreign_2 = models.ForeignKey(
                Target, models.CASCADE, related_name="src_safe"
            )

            m2m_1 = models.ManyToManyField(Target, related_name="id")
            m2m_2 = models.ManyToManyField(Target, related_name="src_safe")

        self.assertEqual(
            Model.check(),
            [
                Error(
                    "Reverse accessor 'Target.id' for "
                    "'invalid_models_tests.Model.foreign_1' clashes with field "
                    "name 'invalid_models_tests.Target.id'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.id', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.foreign_1'."
                    ),
                    obj=Model._meta.get_field("foreign_1"),
                    id="fields.E302",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.foreign_1' "
                    "clashes with field name 'invalid_models_tests.Target.id'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.id', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.foreign_1'."
                    ),
                    obj=Model._meta.get_field("foreign_1"),
                    id="fields.E303",
                ),
                Error(
                    "Reverse accessor 'Target.id' for "
                    "'invalid_models_tests.Model.foreign_1' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.m2m_1'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.foreign_1' or "
                        "'invalid_models_tests.Model.m2m_1'."
                    ),
                    obj=Model._meta.get_field("foreign_1"),
                    id="fields.E304",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.foreign_1' "
                    "clashes with reverse query name for "
                    "'invalid_models_tests.Model.m2m_1'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.foreign_1' or "
                        "'invalid_models_tests.Model.m2m_1'."
                    ),
                    obj=Model._meta.get_field("foreign_1"),
                    id="fields.E305",
                ),
                Error(
                    "Reverse accessor 'Target.src_safe' for "
                    "'invalid_models_tests.Model.foreign_2' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.m2m_2'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.foreign_2' or "
                        "'invalid_models_tests.Model.m2m_2'."
                    ),
                    obj=Model._meta.get_field("foreign_2"),
                    id="fields.E304",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.foreign_2' "
                    "clashes with reverse query name for "
                    "'invalid_models_tests.Model.m2m_2'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.foreign_2' or "
                        "'invalid_models_tests.Model.m2m_2'."
                    ),
                    obj=Model._meta.get_field("foreign_2"),
                    id="fields.E305",
                ),
                Error(
                    "Reverse accessor 'Target.id' for "
                    "'invalid_models_tests.Model.m2m_1' clashes with field name "
                    "'invalid_models_tests.Target.id'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.id', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.m2m_1'."
                    ),
                    obj=Model._meta.get_field("m2m_1"),
                    id="fields.E302",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.m2m_1' "
                    "clashes with field name 'invalid_models_tests.Target.id'.",
                    hint=(
                        "Rename field 'invalid_models_tests.Target.id', or "
                        "add/change a related_name argument to the definition for "
                        "field 'invalid_models_tests.Model.m2m_1'."
                    ),
                    obj=Model._meta.get_field("m2m_1"),
                    id="fields.E303",
                ),
                Error(
                    "Reverse accessor 'Target.id' for "
                    "'invalid_models_tests.Model.m2m_1' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.foreign_1'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.m2m_1' or "
                        "'invalid_models_tests.Model.foreign_1'."
                    ),
                    obj=Model._meta.get_field("m2m_1"),
                    id="fields.E304",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.m2m_1' "
                    "clashes with reverse query name for "
                    "'invalid_models_tests.Model.foreign_1'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.m2m_1' or "
                        "'invalid_models_tests.Model.foreign_1'."
                    ),
                    obj=Model._meta.get_field("m2m_1"),
                    id="fields.E305",
                ),
                Error(
                    "Reverse accessor 'Target.src_safe' for "
                    "'invalid_models_tests.Model.m2m_2' clashes with reverse "
                    "accessor for 'invalid_models_tests.Model.foreign_2'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.m2m_2' or "
                        "'invalid_models_tests.Model.foreign_2'."
                    ),
                    obj=Model._meta.get_field("m2m_2"),
                    id="fields.E304",
                ),
                Error(
                    "Reverse query name for 'invalid_models_tests.Model.m2m_2' "
                    "clashes with reverse query name for "
                    "'invalid_models_tests.Model.foreign_2'.",
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Model.m2m_2' or "
                        "'invalid_models_tests.Model.foreign_2'."
                    ),
                    obj=Model._meta.get_field("m2m_2"),
                    id="fields.E305",
                ),
            ],
        )

    def test_clash_parent_link(self):
        class Parent(models.Model):
            pass

        class Child(Parent):
            other_parent = models.OneToOneField(Parent, models.CASCADE)

        errors = [
            (
                "fields.E304",
                "accessor",
                " 'Parent.child'",
                "parent_ptr",
                "other_parent",
            ),
            ("fields.E305", "query name", "", "parent_ptr", "other_parent"),
            (
                "fields.E304",
                "accessor",
                " 'Parent.child'",
                "other_parent",
                "parent_ptr",
            ),
            ("fields.E305", "query name", "", "other_parent", "parent_ptr"),
        ]
        self.assertEqual(
            Child.check(),
            [
                Error(
                    "Reverse %s%s for 'invalid_models_tests.Child.%s' clashes with "
                    "reverse %s for 'invalid_models_tests.Child.%s'."
                    % (attr, rel_name, field_name, attr, clash_name),
                    hint=(
                        "Add or change a related_name argument to the definition "
                        "for 'invalid_models_tests.Child.%s' or "
                        "'invalid_models_tests.Child.%s'." % (field_name, clash_name)
                    ),
                    obj=Child._meta.get_field(field_name),
                    id=error_id,
                )
                for error_id, attr, rel_name, field_name, clash_name in errors
            ],
        )


@isolate_apps("invalid_models_tests")
class M2mThroughFieldsTests(SimpleTestCase):
    def test_m2m_field_argument_validation(self):
        """
        ManyToManyField accepts the ``through_fields`` kwarg
        only if an intermediary table is specified.
        """

        class Fan(models.Model):
            pass

        with self.assertRaisesMessage(
            ValueError, "Cannot specify through_fields without a through model"
        ):
            models.ManyToManyField(Fan, through_fields=("f1", "f2"))

    def test_invalid_order(self):
        """
        Mixing up the order of link fields to ManyToManyField.through_fields
        triggers validation errors.
        """

        class Fan(models.Model):
            pass

        class Event(models.Model):
            invitees = models.ManyToManyField(
                Fan, through="Invitation", through_fields=("invitee", "event")
            )

        class Invitation(models.Model):
            event = models.ForeignKey(Event, models.CASCADE)
            invitee = models.ForeignKey(Fan, models.CASCADE)
            inviter = models.ForeignKey(Fan, models.CASCADE, related_name="+")

        field = Event._meta.get_field("invitees")
        self.assertEqual(
            field.check(from_model=Event),
            [
                Error(
                    "'Invitation.invitee' is not a foreign key to 'Event'.",
                    hint=(
                        "Did you mean one of the following foreign keys to 'Event': "
                        "event?"
                    ),
                    obj=field,
                    id="fields.E339",
                ),
                Error(
                    "'Invitation.event' is not a foreign key to 'Fan'.",
                    hint=(
                        "Did you mean one of the following foreign keys to 'Fan': "
                        "invitee, inviter?"
                    ),
                    obj=field,
                    id="fields.E339",
                ),
            ],
        )

    def test_invalid_field(self):
        """
        Providing invalid field names to ManyToManyField.through_fields
        triggers validation errors.
        """

        class Fan(models.Model):
            pass

        class Event(models.Model):
            invitees = models.ManyToManyField(
                Fan,
                through="Invitation",
                through_fields=("invalid_field_1", "invalid_field_2"),
            )

        class Invitation(models.Model):
            event = models.ForeignKey(Event, models.CASCADE)
            invitee = models.ForeignKey(Fan, models.CASCADE)
            inviter = models.ForeignKey(Fan, models.CASCADE, related_name="+")

        field = Event._meta.get_field("invitees")
        self.assertEqual(
            field.check(from_model=Event),
            [
                Error(
                    "The intermediary model 'invalid_models_tests.Invitation' has no "
                    "field 'invalid_field_1'.",
                    hint=(
                        "Did you mean one of the following foreign keys to 'Event': "
                        "event?"
                    ),
                    obj=field,
                    id="fields.E338",
                ),
                Error(
                    "The intermediary model 'invalid_models_tests.Invitation' has no "
                    "field 'invalid_field_2'.",
                    hint=(
                        "Did you mean one of the following foreign keys to 'Fan': "
                        "invitee, inviter?"
                    ),
                    obj=field,
                    id="fields.E338",
                ),
            ],
        )

    def test_explicit_field_names(self):
        """
        If ``through_fields`` kwarg is given, it must specify both
        link fields of the intermediary table.
        """

        class Fan(models.Model):
            pass

        class Event(models.Model):
            invitees = models.ManyToManyField(
                Fan, through="Invitation", through_fields=(None, "invitee")
            )

        class Invitation(models.Model):
            event = models.ForeignKey(Event, models.CASCADE)
            invitee = models.ForeignKey(Fan, models.CASCADE)
            inviter = models.ForeignKey(Fan, models.CASCADE, related_name="+")

        field = Event._meta.get_field("invitees")
        self.assertEqual(
            field.check(from_model=Event),
            [
                Error(
                    "Field specifies 'through_fields' but does not provide the names "
                    "of the two link fields that should be used for the relation "
                    "through model 'invalid_models_tests.Invitation'.",
                    hint=(
                        "Make sure you specify 'through_fields' as "
                        "through_fields=('field1', 'field2')"
                    ),
                    obj=field,
                    id="fields.E337",
                ),
            ],
        )

    def test_superset_foreign_object(self):
        class Parent(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            c = models.PositiveIntegerField()

            class Meta:
                unique_together = (("a", "b", "c"),)

        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            value = models.CharField(max_length=255)
            parent = models.ForeignObject(
                Parent,
                on_delete=models.SET_NULL,
                from_fields=("a", "b"),
                to_fields=("a", "b"),
                related_name="children",
            )

        field = Child._meta.get_field("parent")
        self.assertEqual(
            field.check(from_model=Child),
            [
                Error(
                    "No subset of the fields 'a', 'b' on model 'Parent' is unique.",
                    hint=(
                        "Mark a single field as unique=True or add a set of "
                        "fields to a unique constraint (via unique_together or a "
                        "UniqueConstraint (without condition) in the model "
                        "Meta.constraints)."
                    ),
                    obj=field,
                    id="fields.E310",
                ),
            ],
        )

    def test_intersection_foreign_object(self):
        class Parent(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            c = models.PositiveIntegerField()
            d = models.PositiveIntegerField()

            class Meta:
                unique_together = (("a", "b", "c"),)

        class Child(models.Model):
            a = models.PositiveIntegerField()
            b = models.PositiveIntegerField()
            d = models.PositiveIntegerField()
            value = models.CharField(max_length=255)
            parent = models.ForeignObject(
                Parent,
                on_delete=models.SET_NULL,
                from_fields=("a", "b", "d"),
                to_fields=("a", "b", "d"),
                related_name="children",
            )

        field = Child._meta.get_field("parent")
        self.assertEqual(
            field.check(from_model=Child),
            [
                Error(
                    "No subset of the fields 'a', 'b', 'd' on model 'Parent' is "
                    "unique.",
                    hint=(
                        "Mark a single field as unique=True or add a set of "
                        "fields to a unique constraint (via unique_together or a "
                        "UniqueConstraint (without condition) in the model "
                        "Meta.constraints)."
                    ),
                    obj=field,
                    id="fields.E310",
                ),
            ],
        )
