import copy
import sys
import unittest

from django.core.management.validation import get_validation_errors
#from django.core.verification import Error ## cannot import because not implemented yet
## So we need `Error` mock:
Error = lambda *args, **kwargs: None

from django.db import connection, models
from django.db.models.loading import cache, load_app
from django.test.utils import override_settings
from django.utils.six import StringIO

from .models import Person, Group, FKTarget


class InvalidModelTestCase(unittest.TestCase):
    """Import an appliation with invalid models and test the exceptions."""

    def setUp(self):
        # Make sure sys.stdout is not a tty so that we get errors without
        # coloring attached (makes matching the results easier). We restore
        # sys.stderr afterwards.
        self.old_stdout = sys.stdout
        self.stdout = StringIO()
        sys.stdout = self.stdout

        # This test adds dummy applications to the app cache. These
        # need to be removed in order to prevent bad interactions
        # with the flush operation in other tests.
        self.old_app_models = copy.deepcopy(cache.app_models)
        self.old_app_store = copy.deepcopy(cache.app_store)

    def tearDown(self):
        cache.app_models = self.old_app_models
        cache.app_store = self.old_app_store
        cache._get_models_cache = {}
        sys.stdout = self.old_stdout

    # Technically, this isn't an override -- TEST_SWAPPED_MODEL must be
    # set to *something* in order for the test to work. However, it's
    # easier to set this up as an override than to require every developer
    # to specify a value in their test settings.
    @override_settings(
        TEST_SWAPPED_MODEL='invalid_models.ReplacementModel',
        TEST_SWAPPED_MODEL_BAD_VALUE='not-a-model',
        TEST_SWAPPED_MODEL_BAD_MODEL='not_an_app.Target',
    )
    def test_invalid_models(self):
        try:
            module = load_app("invalid_models.invalid_models")
        except Exception:
            self.fail('Unable to load invalid model module')

        get_validation_errors(self.stdout, module)
        self.stdout.seek(0)
        error_log = self.stdout.read()
        actual = error_log.split('\n')
        expected = module.model_errors.split('\n')

        unexpected = [err for err in actual if err not in expected]
        missing = [err for err in expected if err not in actual]
        self.assertFalse(unexpected, "Unexpected Errors: " + '\n'.join(unexpected))
        self.assertFalse(missing, "Missing Errors: " + '\n'.join(missing))

"""
## A declarative way of defining tests.

class NewTests(unittest.TestCase):

    tests = [
        (   
            models.CharField(), 
            Error('CharFields require a "max_length" attribute that is a positive integer.',
                hint='Set "max_length" attribute.')
        ),
        (   
            models.CharField(max_length=-1),
            Error('CharFields require a "max_length" attribute that is a positive integer.',
                hint='Change "max_length" attribute to sth positive.')
        ),
        (   
            models.CharField(max_length="bad"),
            Error('CharFields require a "max_length" attribute that is a positive integer.',
                hint='Set "max_length" attribute.'),
        ),
        (   
            models.DecimalField(),
            [
                Error('DecimalFields require a "decimal_places" attribute that is a non-negative integer.',
                    hint=''),
                Error('DecimalFields require a "max_digits" attribute that is a positive integer.',
                    hint=''),
            ],
        ),
        (   
            models.DecimalField(max_digits=-1, decimal_places=-1),
            [
                Error('DecimalFields require a "decimal_places" attribute that is a non-negative integer.',
                    hint=''),
                Error('DecimalFields require a "max_digits" attribute that is a positive integer.',
                    hint=''),
            ],
        ),
        (   
            models.DecimalField(max_digits="bad", decimal_places="bad"),
            [
                Error('DecimalFields require a "decimal_places" attribute that is a non-negative integer.',
                    hint=''),
                Error('DecimalFields require a "max_digits" attribute that is a positive integer.',
                    hint=''),
            ],
        ),
        (   
            models.DecimalField(max_digits=9, decimal_places=10),
            [
                Error('DecimalFields require a "max_digits" attribute value that is greater than or equal to the value of the "decimal_places" attribute.',
                    hint=''),
            ],
        ),
        (   
            models.DecimalField(max_digits=10, decimal_places=10),
            [],
        ),
        (   
            models.FileField(),
            Error('FileFields require an "upload_to" attribute.',
                hint=''),
        ),
        (   
            models.CharField(max_length=10, choices='bad'),
            Error('"choices" should be iterable (e.g., a tuple or list).',
                hint=''),
        ),
        (   
            models.CharField(max_length=10, choices=[(1, 2, 3), (1, 2, 3)]),
            Error('"choices" should be a sequence of two-item iterables (e.g. list of 2 item tuples).',
                hint=''),
        ),
        (   
            models.CharField(max_length=10, choices=[(1, 2, 3), (1, 2, 3)]),
            Error('"choices" should be a sequence of two-item iterables (e.g. list of 2 item tuples).',
                hint=''),
        ),
        (   
            models.CharField(max_length=10, db_index='bad'),
            Error('"db_index" should be either None, True or False.',
                hint=''),
        ),
        (   
            models.BooleanField(null=True),
            Error('BooleanFields do not accept null values. Use a NullBooleanField instead.',
                hint=''),
        ),
        (   
            models.GenericIPAddressField(null=False, blank=True),
            Error('GenericIPAddressField can not accept blank values if null values are not allowed, as blank values are stored as null.',
                hint=''),
        ),
    ]

    def test_field_errors(self):
        for field, expected_error in self.tests:
            if not isinstance(expected_error, (list, tuple)):
                expected_error = [expected_error]
            self.assertEqual(field.verify(), expected_error)

## I rejected this idea because the following code is better: it isn't longer
## and is much more flexible.
"""

# Models are verified only if DEBUG is set to True.
@override_settings(DEBUG=True)
class CharFieldTests(unittest.TestCase):
    
    def test_max_length_required(self):
        field = models.CharField()
        self.assertEqual(list(field.verify()), [
            Error('CharFields require a "max_length" attribute that is a positive integer.',
                hint=''),
        ])

    def test_max_length_must_be_positive(self):
        field = models.CharField(max_length=-1)
        self.assertEqual(list(field.verify()), [
            Error('"charfield2": CharFields require a "max_length" attribute that is a positive integer.',
                hint=''),
        ])

    def test_max_length_must_be_a_number(self):
        field = models.CharField(max_length="bad")
        self.assertEqual(list(field.verify()), [
            Error('"charfield3": CharFields require a "max_length" attribute that is a positive integer.',
                hint=''),
        ])

    def test_choices_must_be_iterable(self):
        field = models.CharField(max_length=10, choices='bad')
        self.assertEqual(list(field.verify()), [
            Error('"choices": "choices" should be iterable (e.g., a tuple or list).',
                hint=''),
        ])

    def test_choices_must_be_a_sequence_of_pairs(self):
        field = models.CharField(max_length=10, choices=[(1, 2, 3), (1, 2, 3)])
        self.assertEqual(list(field.verify()), [
            Error('"choices2": "choices" should be a sequence of two-item iterables (e.g. list of 2 item tuples).',
                hint=''),
            Error('"choices2": "choices" should be a sequence of two-item iterables (e.g. list of 2 item tuples).',
                hint=''),
        ])

    def test_db_index_type(self):
        field = models.CharField(max_length=10, db_index='bad')
        self.assertEqual(list(field.verify()), [
            Error('"index": "db_index" should be either None, True or False.',
                hint=''),
        ])


# Models are verified only if DEBUG is set to True.
@override_settings(DEBUG=True)
class DecimalFieldTests(unittest.TestCase):

    def test_required_attributes(self):
        field = models.DecimalField()
        self.assertEqual(list(field.verify()), [
            Error('"decimalfield": DecimalFields require a "decimal_places" attribute that is a non-negative integer.',
                hint=''),
            Error('"decimalfield": DecimalFields require a "max_digits" attribute that is a positive integer.',
                hint=''),
        ])

    def test_max_digit_and_decimal_places_must_be_positive(self):
        field = models.DecimalField(max_digits=-1, decimal_places=-1)
        self.assertEqual(list(field.verify()), [
            Error('"decimalfield2": DecimalFields require a "decimal_places" attribute that is a non-negative integer.',
                hint=''),
            Error('"decimalfield2": DecimalFields require a "max_digits" attribute that is a positive integer.',
                hint=''),
        ])

    def test_max_digit_and_decimal_places_must_be_numbers(self):
        field = models.DecimalField(max_digits="bad", decimal_places="bad")
        self.assertEqual(list(field.verify()), [
            Error('"decimalfield3": DecimalFields require a "decimal_places" attribute that is a non-negative integer.',
                hint=''),
            Error('"decimalfield3": DecimalFields require a "max_digits" attribute that is a positive integer.',
                hint=''),
        ])

    def test_decimal_places_cannot_be_too_large(self):
        field = models.DecimalField(max_digits=9, decimal_places=10)
        self.assertEqual(list(field.verify()), [
            Error('"decimalfield4": DecimalFields require a "max_digits" attribute value that is greater than or equal to the value of the "decimal_places" attribute.',
                hint=''),
        ])

    def test_valid_field(self):
        field = models.DecimalField(max_digits=10, decimal_places=10)
        self.assertEqual(list(field.verify()), [])


# Models are verified only if DEBUG is set to True.
@override_settings(DEBUG=True)
class RelativeFieldsTests(unittest.TestCase):

    def test_foreign_key_with_invalid_model(self):
        field = models.ForeignKey("Rel1")
        self.assertEqual(list(field.verify()), [
            Error("The field has a relation with model Rel1, which has either not been installed or is abstract.",
                hint=''),
        ])

    def test_many_to_many_with_invalid_model(self):
        field = models.ManyToManyField("Rel2")
        self.assertEqual(list(field.verify()), [
            Error("The field has an m2m relation with model Rel2, which has either not been installed or is abstract.",
                hint=''),
        ])

    def test_ambiguous_relationship_model(self):
        field = models.ManyToManyField(Person, through="RelationshipDoubleFK", related_name="tertiary")
        self.assertEqual(list(field.verify()), [
            Error("group: Intermediary model RelationshipDoubleFK has more than one foreign key to Person, which is ambiguous and is not permitted.",
                hint=''),
        ])

    def test_relationship_model_with_foreign_key_to_wrong_model(self):
        field = models.ManyToManyField(Person, through="Membership")
        self.assertEqual(list(field.verify()), [
            Error("grouptwo: The field is a manually-defined m2m relation through model Membership, which does not have foreign keys to Person and GroupTwo",
                hint=''),
        ]) 

    def test_relationship_model_missing_foreign_key(self):
        field = models.ManyToManyField(Group, through="MembershipMissingFK")
        self.assertEqual(list(field.verify()), [
            Error("grouptwo: 'secondary' is a manually-defined m2m relation through model MembershipMissingFK, which does not have foreign keys to Group and GroupTwo",
                hint=''),
        ]) 

    def test_missing_relationship_model(self):
        field = models.ManyToManyField(Person, through="MissingM2MModel")
        self.assertEqual(list(field.verify()), [
            Error("The field specifies an m2m relation through model MissingM2MModel, which has not been installed.",
                hint=''),
        ])

    def test_symetrical_self_referential_field(self):
        field = models.ManyToManyField('self', through="Relationship")
        self.assertEqual(list(field.verify()), [
            Error("personselfrefm2m: Many-to-many fields with intermediate tables cannot be symmetrical.",
                hint=''),
        ])

    def test_too_many_foreign_keys_in_self_referential_model(self):
        field = models.ManyToManyField('self', through="RelationshipTripleFK")
        self.assertEqual(list(field.verify()), [
            Error("personselfrefm2m: Intermediary model RelationshipTripleFK has more than two foreign keys to PersonSelfRefM2M, which is ambiguous and is not permitted.",
                hint=''),
        ])

    def test_symetric_self_reference_with_relationship(self):
        field = models.ManyToManyField('self', through="ExplicitRelationship", symmetrical=True)
        self.assertEqual(list(field.verify()), [
            Error('personselfrefm2mexplicit: Many-to-many fields with intermediate tables cannot be symmetrical.',
                hint=''),
        ])        

    def test_foreign_key_to_abstract_model_forbidden(self):
        field = models.ForeignKey('AbstractModel')
        self.assertEqual(list(field.verify()), [
            Error("abstractrelationmodel: The field has a relation with model AbstractModel, which has either not been installed or is abstract.",
                hint=''),
        ])  

    def test_m2m_to_abstract_model_forbidden(self):
        field = models.ManyToManyField('AbstractModel')
        self.assertEqual(list(field.verify()), [
            Error("abstractrelationmodel: The field has an m2m relation with model AbstractModel, which has either not been installed or is abstract.",
                hint=''),
        ])        

    def test_unique_m2m_forbidden(self):
        field = models.ManyToManyField(Person, unique=True)
        self.assertEqual(list(field.verify()), [
            Error("uniquem2m: ManyToManyFields cannot be unique.  Remove the unique argument on 'unique_people'.",
                hint=''),
        ])

    def test_foreign_key_to_non_unique_field(self):
        field = models.ForeignKey('FKTarget', to_field='bad')
        self.assertEqual(list(field.verify()), [
            Error("nonuniquefktarget1: Field 'bad' under model 'FKTarget' must have a unique=True constraint.",
                hint=''),
        ])

    def test_foreign_key_to_non_unique_field_2(self):
        field = models.ForeignKey(FKTarget, to_field='bad')
        self.assertEqual(list(field.verify()), [
            Error("nonuniquefktarget1: Field 'bad' under model 'FKTarget' must have a unique=True constraint.",
                hint=''),
        ])

    def test_on_delete_set_null_with_non_nullable_field(self):
        field = models.ForeignKey(Person, on_delete=models.SET_NULL)
        self.assertEqual(list(field.verify()), [
            Error("invalidsetnull: The field specifies on_delete=SET_NULL, but cannot be null.",
                hint=''),
        ])

    def test_on_delete_set_default_without_default_value(self):
        field = models.ForeignKey(Person, on_delete=models.SET_DEFAULT)
        self.assertEqual(list(field.verify()), [
            Error("invalidsetdefault: The field specifies on_delete=SET_DEFAULT, but has no default value.",
                hint=''),
        ])
    
    def test_nullable_primary_key(self):
        field = models.IntegerField(primary_key=True, null=True)
        if connection.features.interprets_empty_strings_as_nulls:
            self.assertEqual(list(field.verify()), [])
        else:
            self.assertEqual(list(field.verify()), [
                Error('primarykeynull: "my_pk_field": Primary key fields cannot have null=True.',
                    hint=''),
            ])


# Models are verified only if DEBUG is set to True.
@override_settings(DEBUG=True)
class OtherFieldTests(unittest.TestCase):

    def test_upload_to_required(self):
        field = models.FileField()
        self.assertEqual(list(field.verify()), [
            Error('"filefield": FileFields require an "upload_to" attribute.',
                hint=''),
        ])

    def test_null_do_not_accepted(self):
        field = models.BooleanField(null=True)
        self.assertEqual(list(field.verify()), [
            Error('"nullbool": BooleanFields do not accept null values. Use a NullBooleanField instead.',
                hint=''),
        ])

    def test_blank_field_must_be_nullable(self):
        field = models.GenericIPAddressField(null=False, blank=True)
        self.assertEqual(list(field.verify()), [
            Error('"generic_ip_notnull_blank": GenericIPAddressField can not accept blank values if null values are not allowed, as blank values are stored as null.',
                hint=''),
        ])
