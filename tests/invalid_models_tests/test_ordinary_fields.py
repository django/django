import unittest
import uuid

from django.core.checks import Error, Warning as DjangoWarning
from django.db import connection, models
from django.test import (
    SimpleTestCase, TestCase, skipIfDBFeature, skipUnlessDBFeature,
)
from django.test.utils import isolate_apps, override_settings
from django.utils.functional import lazy
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.version import get_docs_version


@isolate_apps('invalid_models_tests')
class AutoFieldTests(SimpleTestCase):

    def test_valid_case(self):
        class Model(models.Model):
            id = models.AutoField(primary_key=True)

        field = Model._meta.get_field('id')
        self.assertEqual(field.check(), [])

    def test_primary_key(self):
        # primary_key must be True. Refs #12467.
        class Model(models.Model):
            field = models.AutoField(primary_key=False)

            # Prevent Django from autocreating `id` AutoField, which would
            # result in an error, because a model must have exactly one
            # AutoField.
            another = models.IntegerField(primary_key=True)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                'AutoFields must set primary_key=True.',
                obj=field,
                id='fields.E100',
            ),
        ])

    def test_max_length_warning(self):
        class Model(models.Model):
            auto = models.AutoField(primary_key=True, max_length=2)

        field = Model._meta.get_field('auto')
        self.assertEqual(field.check(), [
            DjangoWarning(
                "'max_length' is ignored when used with %s."
                % field.__class__.__name__,
                hint="Remove 'max_length' from field",
                obj=field,
                id='fields.W122',
            ),
        ])


@isolate_apps('invalid_models_tests')
class BinaryFieldTests(SimpleTestCase):

    def test_valid_default_value(self):
        class Model(models.Model):
            field1 = models.BinaryField(default=b'test')
            field2 = models.BinaryField(default=None)

        for field_name in ('field1', 'field2'):
            field = Model._meta.get_field(field_name)
            self.assertEqual(field.check(), [])

    def test_str_default_value(self):
        class Model(models.Model):
            field = models.BinaryField(default='test')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "BinaryField's default cannot be a string. Use bytes content "
                "instead.",
                obj=field,
                id='fields.E170',
            ),
        ])


@isolate_apps('invalid_models_tests')
class CharFieldTests(TestCase):

    def test_valid_field(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=255,
                choices=[
                    ('1', 'item1'),
                    ('2', 'item2'),
                ],
                db_index=True,
            )

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [])

    def test_missing_max_length(self):
        class Model(models.Model):
            field = models.CharField()

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "CharFields must define a 'max_length' attribute.",
                obj=field,
                id='fields.E120',
            ),
        ])

    def test_negative_max_length(self):
        class Model(models.Model):
            field = models.CharField(max_length=-1)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121',
            ),
        ])

    def test_bad_max_length_value(self):
        class Model(models.Model):
            field = models.CharField(max_length="bad")

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121',
            ),
        ])

    def test_str_max_length_value(self):
        class Model(models.Model):
            field = models.CharField(max_length='20')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121',
            ),
        ])

    def test_str_max_length_type(self):
        class Model(models.Model):
            field = models.CharField(max_length=True)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_length' must be a positive integer.",
                obj=field,
                id='fields.E121'
            ),
        ])

    def test_non_iterable_choices(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices='bad')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable (e.g., a list or tuple).",
                obj=field,
                id='fields.E004',
            ),
        ])

    def test_non_iterable_choices_two_letters(self):
        """Two letters isn't a valid choice pair."""
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=['ab'])

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable containing (actual value, "
                "human readable name) tuples.",
                obj=field,
                id='fields.E005',
            ),
        ])

    def test_iterable_of_iterable_choices(self):
        class ThingItem:
            def __init__(self, value, display):
                self.value = value
                self.display = display

            def __iter__(self):
                return iter((self.value, self.display))

            def __len__(self):
                return 2

        class Things:
            def __iter__(self):
                return iter((ThingItem(1, 2), ThingItem(3, 4)))

        class ThingWithIterableChoices(models.Model):
            thing = models.CharField(max_length=100, blank=True, choices=Things())

        self.assertEqual(ThingWithIterableChoices._meta.get_field('thing').check(), [])

    def test_choices_containing_non_pairs(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=[(1, 2, 3), (1, 2, 3)])

        class Model2(models.Model):
            field = models.IntegerField(choices=[0])

        for model in (Model, Model2):
            with self.subTest(model.__name__):
                field = model._meta.get_field('field')
                self.assertEqual(field.check(), [
                    Error(
                        "'choices' must be an iterable containing (actual "
                        "value, human readable name) tuples.",
                        obj=field,
                        id='fields.E005',
                    ),
                ])

    def test_choices_containing_lazy(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=[['1', _('1')], ['2', _('2')]])

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_lazy_choices(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, choices=lazy(lambda: [[1, '1'], [2, '2']], tuple)())

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_choices_named_group(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10, choices=[
                    ['knights', [['L', 'Lancelot'], ['G', 'Galahad']]],
                    ['wizards', [['T', 'Tim the Enchanter']]],
                    ['R', 'Random character'],
                ],
            )

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_choices_named_group_non_pairs(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10,
                choices=[['knights', [['L', 'Lancelot', 'Du Lac']]]],
            )

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable containing (actual value, "
                "human readable name) tuples.",
                obj=field,
                id='fields.E005',
            ),
        ])

    def test_choices_named_group_bad_structure(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10, choices=[
                    ['knights', [
                        ['Noble', [['G', 'Galahad']]],
                        ['Combative', [['L', 'Lancelot']]],
                    ]],
                ],
            )

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'choices' must be an iterable containing (actual value, "
                "human readable name) tuples.",
                obj=field,
                id='fields.E005',
            ),
        ])

    def test_choices_named_group_lazy(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=10, choices=[
                    [_('knights'), [['L', _('Lancelot')], ['G', _('Galahad')]]],
                    ['R', _('Random character')],
                ],
            )

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_choices_in_max_length(self):
        class Model(models.Model):
            field = models.CharField(
                max_length=2, choices=[
                    ('ABC', 'Value Too Long!'), ('OK', 'Good')
                ],
            )
            group = models.CharField(
                max_length=2, choices=[
                    ('Nested', [('OK', 'Good'), ('Longer', 'Longer')]),
                    ('Grouped', [('Bad', 'Bad')]),
                ],
            )

        for name, choice_max_length in (('field', 3), ('group', 6)):
            with self.subTest(name):
                field = Model._meta.get_field(name)
                self.assertEqual(field.check(), [
                    Error(
                        "'max_length' is too small to fit the longest value "
                        "in 'choices' (%d characters)." % choice_max_length,
                        obj=field,
                        id='fields.E009',
                    ),
                ])

    def test_bad_db_index_value(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, db_index='bad')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'db_index' must be None, True or False.",
                obj=field,
                id='fields.E006',
            ),
        ])

    def test_bad_validators(self):
        class Model(models.Model):
            field = models.CharField(max_length=10, validators=[True])

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "All 'validators' must be callable.",
                hint=(
                    "validators[0] (True) isn't a function or instance of a "
                    "validator class."
                ),
                obj=field,
                id='fields.E008',
            ),
        ])

    @unittest.skipUnless(connection.vendor == 'mysql',
                         "Test valid only for MySQL")
    def test_too_long_char_field_under_mysql(self):
        from django.db.backends.mysql.validation import DatabaseValidation

        class Model(models.Model):
            field = models.CharField(unique=True, max_length=256)

        field = Model._meta.get_field('field')
        validator = DatabaseValidation(connection=connection)
        self.assertEqual(validator.check_field(field), [
            DjangoWarning(
                '%s may not allow unique CharFields to have a max_length > '
                '255.' % connection.display_name,
                hint=(
                    'See: https://docs.djangoproject.com/en/%s/ref/databases/'
                    '#mysql-character-fields' % get_docs_version()
                ),
                obj=field,
                id='mysql.W003',
            )
        ])

    def test_db_collation(self):
        class Model(models.Model):
            field = models.CharField(max_length=100, db_collation='anything')

        field = Model._meta.get_field('field')
        error = Error(
            '%s does not support a database collation on CharFields.'
            % connection.display_name,
            id='fields.E190',
            obj=field,
        )
        expected = [] if connection.features.supports_collation_on_charfield else [error]
        self.assertEqual(field.check(databases=self.databases), expected)

    def test_db_collation_required_db_features(self):
        class Model(models.Model):
            field = models.CharField(max_length=100, db_collation='anything')

            class Meta:
                required_db_features = {'supports_collation_on_charfield'}

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(databases=self.databases), [])


@isolate_apps('invalid_models_tests')
class DateFieldTests(SimpleTestCase):
    maxDiff = None

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
        self.assertEqual(errors, [
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
        ])

    @override_settings(USE_TZ=True)
    def test_fix_default_value_tz(self):
        self.test_fix_default_value()


@isolate_apps('invalid_models_tests')
class DateTimeFieldTests(SimpleTestCase):
    maxDiff = None

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
        self.assertEqual(errors, [
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
        ])

    @override_settings(USE_TZ=True)
    def test_fix_default_value_tz(self):
        self.test_fix_default_value()


@isolate_apps('invalid_models_tests')
class DecimalFieldTests(SimpleTestCase):

    def test_required_attributes(self):
        class Model(models.Model):
            field = models.DecimalField()

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "DecimalFields must define a 'decimal_places' attribute.",
                obj=field,
                id='fields.E130',
            ),
            Error(
                "DecimalFields must define a 'max_digits' attribute.",
                obj=field,
                id='fields.E132',
            ),
        ])

    def test_negative_max_digits_and_decimal_places(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits=-1, decimal_places=-1)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'decimal_places' must be a non-negative integer.",
                obj=field,
                id='fields.E131',
            ),
            Error(
                "'max_digits' must be a positive integer.",
                obj=field,
                id='fields.E133',
            ),
        ])

    def test_bad_values_of_max_digits_and_decimal_places(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits="bad", decimal_places="bad")

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'decimal_places' must be a non-negative integer.",
                obj=field,
                id='fields.E131',
            ),
            Error(
                "'max_digits' must be a positive integer.",
                obj=field,
                id='fields.E133',
            ),
        ])

    def test_decimal_places_greater_than_max_digits(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits=9, decimal_places=10)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'max_digits' must be greater or equal to 'decimal_places'.",
                obj=field,
                id='fields.E134',
            ),
        ])

    def test_valid_field(self):
        class Model(models.Model):
            field = models.DecimalField(max_digits=10, decimal_places=10)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [])


@isolate_apps('invalid_models_tests')
class FileFieldTests(SimpleTestCase):

    def test_valid_default_case(self):
        class Model(models.Model):
            field = models.FileField()

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_valid_case(self):
        class Model(models.Model):
            field = models.FileField(upload_to='somewhere')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [])

    def test_primary_key(self):
        class Model(models.Model):
            field = models.FileField(primary_key=False, upload_to='somewhere')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "'primary_key' is not a valid argument for a FileField.",
                obj=field,
                id='fields.E201',
            )
        ])

    def test_upload_to_starts_with_slash(self):
        class Model(models.Model):
            field = models.FileField(upload_to='/somewhere')

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "FileField's 'upload_to' argument must be a relative path, not "
                "an absolute path.",
                obj=field,
                id='fields.E202',
                hint='Remove the leading slash.',
            )
        ])

    def test_upload_to_callable_not_checked(self):
        def callable(instance, filename):
            return '/' + filename

        class Model(models.Model):
            field = models.FileField(upload_to=callable)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [])


@isolate_apps('invalid_models_tests')
class FilePathFieldTests(SimpleTestCase):

    def test_forbidden_files_and_folders(self):
        class Model(models.Model):
            field = models.FilePathField(allow_files=False, allow_folders=False)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                "FilePathFields must have either 'allow_files' or 'allow_folders' set to True.",
                obj=field,
                id='fields.E140',
            ),
        ])


@isolate_apps('invalid_models_tests')
class GenericIPAddressFieldTests(SimpleTestCase):

    def test_non_nullable_blank(self):
        class Model(models.Model):
            field = models.GenericIPAddressField(null=False, blank=True)

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(), [
            Error(
                ('GenericIPAddressFields cannot have blank=True if null=False, '
                 'as blank values are stored as nulls.'),
                obj=field,
                id='fields.E150',
            ),
        ])


@isolate_apps('invalid_models_tests')
class ImageFieldTests(SimpleTestCase):

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
                hint=('Get Pillow at https://pypi.org/project/Pillow/ '
                      'or run command "python -m pip install Pillow".'),
                obj=field,
                id='fields.E210',
            ),
        ]
        self.assertEqual(errors, expected)


@isolate_apps('invalid_models_tests')
class IntegerFieldTests(SimpleTestCase):

    def test_max_length_warning(self):
        class Model(models.Model):
            integer = models.IntegerField(max_length=2)
            biginteger = models.BigIntegerField(max_length=2)
            smallinteger = models.SmallIntegerField(max_length=2)
            positiveinteger = models.PositiveIntegerField(max_length=2)
            positivebiginteger = models.PositiveBigIntegerField(max_length=2)
            positivesmallinteger = models.PositiveSmallIntegerField(max_length=2)

        for field in Model._meta.get_fields():
            if field.auto_created:
                continue
            with self.subTest(name=field.name):
                self.assertEqual(field.check(), [
                    DjangoWarning(
                        "'max_length' is ignored when used with %s." % field.__class__.__name__,
                        hint="Remove 'max_length' from field",
                        obj=field,
                        id='fields.W122',
                    )
                ])


@isolate_apps('invalid_models_tests')
class TimeFieldTests(SimpleTestCase):
    maxDiff = None

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
        self.assertEqual(errors, [
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
        ])

    @override_settings(USE_TZ=True)
    def test_fix_default_value_tz(self):
        self.test_fix_default_value()


@isolate_apps('invalid_models_tests')
class TextFieldTests(TestCase):

    @skipIfDBFeature('supports_index_on_text_field')
    def test_max_length_warning(self):
        class Model(models.Model):
            value = models.TextField(db_index=True)
        field = Model._meta.get_field('value')
        field_type = field.db_type(connection)
        self.assertEqual(field.check(databases=self.databases), [
            DjangoWarning(
                '%s does not support a database index on %s columns.'
                % (connection.display_name, field_type),
                hint=(
                    "An index won't be created. Silence this warning if you "
                    "don't care about it."
                ),
                obj=field,
                id='fields.W162',
            )
        ])

    def test_db_collation(self):
        class Model(models.Model):
            field = models.TextField(db_collation='anything')

        field = Model._meta.get_field('field')
        error = Error(
            '%s does not support a database collation on TextFields.'
            % connection.display_name,
            id='fields.E190',
            obj=field,
        )
        expected = [] if connection.features.supports_collation_on_textfield else [error]
        self.assertEqual(field.check(databases=self.databases), expected)

    def test_db_collation_required_db_features(self):
        class Model(models.Model):
            field = models.TextField(db_collation='anything')

            class Meta:
                required_db_features = {'supports_collation_on_textfield'}

        field = Model._meta.get_field('field')
        self.assertEqual(field.check(databases=self.databases), [])


@isolate_apps('invalid_models_tests')
class UUIDFieldTests(TestCase):
    def test_choices_named_group(self):
        class Model(models.Model):
            field = models.UUIDField(
                choices=[
                    ['knights', [
                        [uuid.UUID('5c859437-d061-4847-b3f7-e6b78852f8c8'), 'Lancelot'],
                        [uuid.UUID('c7853ec1-2ea3-4359-b02d-b54e8f1bcee2'), 'Galahad'],
                    ]],
                    [uuid.UUID('25d405be-4895-4d50-9b2e-d6695359ce47'), 'Other'],
                ],
            )

        self.assertEqual(Model._meta.get_field('field').check(), [])


@isolate_apps('invalid_models_tests')
@skipUnlessDBFeature('supports_json_field')
class JSONFieldTests(TestCase):
    def test_invalid_default(self):
        class Model(models.Model):
            field = models.JSONField(default={})

        self.assertEqual(Model._meta.get_field('field').check(), [
            DjangoWarning(
                msg=(
                    "JSONField default should be a callable instead of an "
                    "instance so that it's not shared between all field "
                    "instances."
                ),
                hint=(
                    'Use a callable instead, e.g., use `dict` instead of `{}`.'
                ),
                obj=Model._meta.get_field('field'),
                id='fields.E010',
            )
        ])

    def test_valid_default(self):
        class Model(models.Model):
            field = models.JSONField(default=dict)

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_valid_default_none(self):
        class Model(models.Model):
            field = models.JSONField(default=None)

        self.assertEqual(Model._meta.get_field('field').check(), [])

    def test_valid_callable_default(self):
        def callable_default():
            return {'it': 'works'}

        class Model(models.Model):
            field = models.JSONField(default=callable_default)

        self.assertEqual(Model._meta.get_field('field').check(), [])
