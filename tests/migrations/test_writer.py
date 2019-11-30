import datetime
import decimal
import enum
import functools
import math
import os
import re
import uuid
from unittest import mock

import custom_migration_operations.more_operations
import custom_migration_operations.operations

from django import get_version
from django.conf import SettingsReference, settings
from django.core.validators import EmailValidator, RegexValidator
from django.db import migrations, models
from django.db.migrations.serializer import BaseSerializer
from django.db.migrations.writer import MigrationWriter, OperationWriter
from django.test import SimpleTestCase
from django.utils.deconstruct import deconstructible
from django.utils.functional import SimpleLazyObject
from django.utils.timezone import get_default_timezone, get_fixed_timezone, utc
from django.utils.translation import gettext_lazy as _

from .models import FoodManager, FoodQuerySet


class DeconstructibleInstances:
    def deconstruct(self):
        return ('DeconstructibleInstances', [], {})


class Money(decimal.Decimal):
    def deconstruct(self):
        return (
            '%s.%s' % (self.__class__.__module__, self.__class__.__name__),
            [str(self)],
            {}
        )


class TestModel1:
    def upload_to(self):
        return '/somewhere/dynamic/'
    thing = models.FileField(upload_to=upload_to)


class TextEnum(enum.Enum):
    A = 'a-value'
    B = 'value-b'


class TextTranslatedEnum(enum.Enum):
    A = _('a-value')
    B = _('value-b')


class BinaryEnum(enum.Enum):
    A = b'a-value'
    B = b'value-b'


class IntEnum(enum.IntEnum):
    A = 1
    B = 2


class OperationWriterTests(SimpleTestCase):

    def test_empty_signature(self):
        operation = custom_migration_operations.operations.TestOperation()
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            'custom_migration_operations.operations.TestOperation(\n'
            '),'
        )

    def test_args_signature(self):
        operation = custom_migration_operations.operations.ArgsOperation(1, 2)
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            'custom_migration_operations.operations.ArgsOperation(\n'
            '    arg1=1,\n'
            '    arg2=2,\n'
            '),'
        )

    def test_kwargs_signature(self):
        operation = custom_migration_operations.operations.KwargsOperation(kwarg1=1)
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            'custom_migration_operations.operations.KwargsOperation(\n'
            '    kwarg1=1,\n'
            '),'
        )

    def test_args_kwargs_signature(self):
        operation = custom_migration_operations.operations.ArgsKwargsOperation(1, 2, kwarg2=4)
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            'custom_migration_operations.operations.ArgsKwargsOperation(\n'
            '    arg1=1,\n'
            '    arg2=2,\n'
            '    kwarg2=4,\n'
            '),'
        )

    def test_nested_args_signature(self):
        operation = custom_migration_operations.operations.ArgsOperation(
            custom_migration_operations.operations.ArgsOperation(1, 2),
            custom_migration_operations.operations.KwargsOperation(kwarg1=3, kwarg2=4)
        )
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            'custom_migration_operations.operations.ArgsOperation(\n'
            '    arg1=custom_migration_operations.operations.ArgsOperation(\n'
            '        arg1=1,\n'
            '        arg2=2,\n'
            '    ),\n'
            '    arg2=custom_migration_operations.operations.KwargsOperation(\n'
            '        kwarg1=3,\n'
            '        kwarg2=4,\n'
            '    ),\n'
            '),'
        )

    def test_multiline_args_signature(self):
        operation = custom_migration_operations.operations.ArgsOperation("test\n    arg1", "test\narg2")
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            "custom_migration_operations.operations.ArgsOperation(\n"
            "    arg1='test\\n    arg1',\n"
            "    arg2='test\\narg2',\n"
            "),"
        )

    def test_expand_args_signature(self):
        operation = custom_migration_operations.operations.ExpandArgsOperation([1, 2])
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            'custom_migration_operations.operations.ExpandArgsOperation(\n'
            '    arg=[\n'
            '        1,\n'
            '        2,\n'
            '    ],\n'
            '),'
        )

    def test_nested_operation_expand_args_signature(self):
        operation = custom_migration_operations.operations.ExpandArgsOperation(
            arg=[
                custom_migration_operations.operations.KwargsOperation(
                    kwarg1=1,
                    kwarg2=2,
                ),
            ]
        )
        buff, imports = OperationWriter(operation, indentation=0).serialize()
        self.assertEqual(imports, {'import custom_migration_operations.operations'})
        self.assertEqual(
            buff,
            'custom_migration_operations.operations.ExpandArgsOperation(\n'
            '    arg=[\n'
            '        custom_migration_operations.operations.KwargsOperation(\n'
            '            kwarg1=1,\n'
            '            kwarg2=2,\n'
            '        ),\n'
            '    ],\n'
            '),'
        )


class WriterTests(SimpleTestCase):
    """
    Tests the migration writer (makes migration files from Migration instances)
    """
    class NestedEnum(enum.IntEnum):
        A = 1
        B = 2

    class NestedChoices(models.TextChoices):
        X = 'X', 'X value'
        Y = 'Y', 'Y value'

    def safe_exec(self, string, value=None):
        d = {}
        try:
            exec(string, globals(), d)
        except Exception as e:
            if value:
                self.fail("Could not exec %r (from value %r): %s" % (string.strip(), value, e))
            else:
                self.fail("Could not exec %r: %s" % (string.strip(), e))
        return d

    def serialize_round_trip(self, value):
        string, imports = MigrationWriter.serialize(value)
        return self.safe_exec("%s\ntest_value_result = %s" % ("\n".join(imports), string), value)['test_value_result']

    def assertSerializedEqual(self, value):
        self.assertEqual(self.serialize_round_trip(value), value)

    def assertSerializedResultEqual(self, value, target):
        self.assertEqual(MigrationWriter.serialize(value), target)

    def assertSerializedFieldEqual(self, value):
        new_value = self.serialize_round_trip(value)
        self.assertEqual(value.__class__, new_value.__class__)
        self.assertEqual(value.max_length, new_value.max_length)
        self.assertEqual(value.null, new_value.null)
        self.assertEqual(value.unique, new_value.unique)

    def test_serialize_numbers(self):
        self.assertSerializedEqual(1)
        self.assertSerializedEqual(1.2)
        self.assertTrue(math.isinf(self.serialize_round_trip(float("inf"))))
        self.assertTrue(math.isinf(self.serialize_round_trip(float("-inf"))))
        self.assertTrue(math.isnan(self.serialize_round_trip(float("nan"))))

        self.assertSerializedEqual(decimal.Decimal('1.3'))
        self.assertSerializedResultEqual(
            decimal.Decimal('1.3'),
            ("Decimal('1.3')", {'from decimal import Decimal'})
        )

        self.assertSerializedEqual(Money('1.3'))
        self.assertSerializedResultEqual(
            Money('1.3'),
            ("migrations.test_writer.Money('1.3')", {'import migrations.test_writer'})
        )

    def test_serialize_constants(self):
        self.assertSerializedEqual(None)
        self.assertSerializedEqual(True)
        self.assertSerializedEqual(False)

    def test_serialize_strings(self):
        self.assertSerializedEqual(b"foobar")
        string, imports = MigrationWriter.serialize(b"foobar")
        self.assertEqual(string, "b'foobar'")
        self.assertSerializedEqual("föobár")
        string, imports = MigrationWriter.serialize("foobar")
        self.assertEqual(string, "'foobar'")

    def test_serialize_multiline_strings(self):
        self.assertSerializedEqual(b"foo\nbar")
        string, imports = MigrationWriter.serialize(b"foo\nbar")
        self.assertEqual(string, "b'foo\\nbar'")
        self.assertSerializedEqual("föo\nbár")
        string, imports = MigrationWriter.serialize("foo\nbar")
        self.assertEqual(string, "'foo\\nbar'")

    def test_serialize_collections(self):
        self.assertSerializedEqual({1: 2})
        self.assertSerializedEqual(["a", 2, True, None])
        self.assertSerializedEqual({2, 3, "eighty"})
        self.assertSerializedEqual({"lalalala": ["yeah", "no", "maybe"]})
        self.assertSerializedEqual(_('Hello'))

    def test_serialize_builtin_types(self):
        self.assertSerializedEqual([list, tuple, dict, set, frozenset])
        self.assertSerializedResultEqual(
            [list, tuple, dict, set, frozenset],
            ("[list, tuple, dict, set, frozenset]", set())
        )

    def test_serialize_lazy_objects(self):
        pattern = re.compile(r'^foo$')
        lazy_pattern = SimpleLazyObject(lambda: pattern)
        self.assertEqual(self.serialize_round_trip(lazy_pattern), pattern)

    def test_serialize_enums(self):
        self.assertSerializedResultEqual(
            TextEnum.A,
            ("migrations.test_writer.TextEnum['A']", {'import migrations.test_writer'})
        )
        self.assertSerializedResultEqual(
            TextTranslatedEnum.A,
            ("migrations.test_writer.TextTranslatedEnum['A']", {'import migrations.test_writer'})
        )
        self.assertSerializedResultEqual(
            BinaryEnum.A,
            ("migrations.test_writer.BinaryEnum['A']", {'import migrations.test_writer'})
        )
        self.assertSerializedResultEqual(
            IntEnum.B,
            ("migrations.test_writer.IntEnum['B']", {'import migrations.test_writer'})
        )
        self.assertSerializedResultEqual(
            self.NestedEnum.A,
            (
                "migrations.test_writer.WriterTests.NestedEnum['A']",
                {'import migrations.test_writer'},
            ),
        )
        self.assertSerializedEqual(self.NestedEnum.A)

        field = models.CharField(default=TextEnum.B, choices=[(m.value, m) for m in TextEnum])
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.CharField(choices=["
            "('a-value', migrations.test_writer.TextEnum['A']), "
            "('value-b', migrations.test_writer.TextEnum['B'])], "
            "default=migrations.test_writer.TextEnum['B'])"
        )
        field = models.CharField(
            default=TextTranslatedEnum.A,
            choices=[(m.value, m) for m in TextTranslatedEnum],
        )
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.CharField(choices=["
            "('a-value', migrations.test_writer.TextTranslatedEnum['A']), "
            "('value-b', migrations.test_writer.TextTranslatedEnum['B'])], "
            "default=migrations.test_writer.TextTranslatedEnum['A'])"
        )
        field = models.CharField(default=BinaryEnum.B, choices=[(m.value, m) for m in BinaryEnum])
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.CharField(choices=["
            "(b'a-value', migrations.test_writer.BinaryEnum['A']), "
            "(b'value-b', migrations.test_writer.BinaryEnum['B'])], "
            "default=migrations.test_writer.BinaryEnum['B'])"
        )
        field = models.IntegerField(default=IntEnum.A, choices=[(m.value, m) for m in IntEnum])
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.IntegerField(choices=["
            "(1, migrations.test_writer.IntEnum['A']), "
            "(2, migrations.test_writer.IntEnum['B'])], "
            "default=migrations.test_writer.IntEnum['A'])"
        )

    def test_serialize_choices(self):
        class TextChoices(models.TextChoices):
            A = 'A', 'A value'
            B = 'B', 'B value'

        class IntegerChoices(models.IntegerChoices):
            A = 1, 'One'
            B = 2, 'Two'

        class DateChoices(datetime.date, models.Choices):
            DATE_1 = 1969, 7, 20, 'First date'
            DATE_2 = 1969, 11, 19, 'Second date'

        self.assertSerializedResultEqual(TextChoices.A, ("'A'", set()))
        self.assertSerializedResultEqual(IntegerChoices.A, ('1', set()))
        self.assertSerializedResultEqual(
            DateChoices.DATE_1,
            ('datetime.date(1969, 7, 20)', {'import datetime'}),
        )
        field = models.CharField(default=TextChoices.B, choices=TextChoices.choices)
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.CharField(choices=[('A', 'A value'), ('B', 'B value')], "
            "default='B')",
        )
        field = models.IntegerField(default=IntegerChoices.B, choices=IntegerChoices.choices)
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.IntegerField(choices=[(1, 'One'), (2, 'Two')], default=2)",
        )
        field = models.DateField(default=DateChoices.DATE_2, choices=DateChoices.choices)
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.DateField(choices=["
            "(datetime.date(1969, 7, 20), 'First date'), "
            "(datetime.date(1969, 11, 19), 'Second date')], "
            "default=datetime.date(1969, 11, 19))"
        )

    def test_serialize_nested_class(self):
        for nested_cls in [self.NestedEnum, self.NestedChoices]:
            cls_name = nested_cls.__name__
            with self.subTest(cls_name):
                self.assertSerializedResultEqual(
                    nested_cls,
                    (
                        "migrations.test_writer.WriterTests.%s" % cls_name,
                        {'import migrations.test_writer'},
                    ),
                )

    def test_serialize_uuid(self):
        self.assertSerializedEqual(uuid.uuid1())
        self.assertSerializedEqual(uuid.uuid4())

        uuid_a = uuid.UUID('5c859437-d061-4847-b3f7-e6b78852f8c8')
        uuid_b = uuid.UUID('c7853ec1-2ea3-4359-b02d-b54e8f1bcee2')
        self.assertSerializedResultEqual(
            uuid_a,
            ("uuid.UUID('5c859437-d061-4847-b3f7-e6b78852f8c8')", {'import uuid'})
        )
        self.assertSerializedResultEqual(
            uuid_b,
            ("uuid.UUID('c7853ec1-2ea3-4359-b02d-b54e8f1bcee2')", {'import uuid'})
        )

        field = models.UUIDField(choices=((uuid_a, 'UUID A'), (uuid_b, 'UUID B')), default=uuid_a)
        string = MigrationWriter.serialize(field)[0]
        self.assertEqual(
            string,
            "models.UUIDField(choices=["
            "(uuid.UUID('5c859437-d061-4847-b3f7-e6b78852f8c8'), 'UUID A'), "
            "(uuid.UUID('c7853ec1-2ea3-4359-b02d-b54e8f1bcee2'), 'UUID B')], "
            "default=uuid.UUID('5c859437-d061-4847-b3f7-e6b78852f8c8'))"
        )

    def test_serialize_functions(self):
        with self.assertRaisesMessage(ValueError, 'Cannot serialize function: lambda'):
            self.assertSerializedEqual(lambda x: 42)
        self.assertSerializedEqual(models.SET_NULL)
        string, imports = MigrationWriter.serialize(models.SET(42))
        self.assertEqual(string, 'models.SET(42)')
        self.serialize_round_trip(models.SET(42))

    def test_serialize_datetime(self):
        self.assertSerializedEqual(datetime.datetime.utcnow())
        self.assertSerializedEqual(datetime.datetime.utcnow)
        self.assertSerializedEqual(datetime.datetime.today())
        self.assertSerializedEqual(datetime.datetime.today)
        self.assertSerializedEqual(datetime.date.today())
        self.assertSerializedEqual(datetime.date.today)
        self.assertSerializedEqual(datetime.datetime.now().time())
        self.assertSerializedEqual(datetime.datetime(2014, 1, 1, 1, 1, tzinfo=get_default_timezone()))
        self.assertSerializedEqual(datetime.datetime(2013, 12, 31, 22, 1, tzinfo=get_fixed_timezone(180)))
        self.assertSerializedResultEqual(
            datetime.datetime(2014, 1, 1, 1, 1),
            ("datetime.datetime(2014, 1, 1, 1, 1)", {'import datetime'})
        )
        self.assertSerializedResultEqual(
            datetime.datetime(2012, 1, 1, 1, 1, tzinfo=utc),
            (
                "datetime.datetime(2012, 1, 1, 1, 1, tzinfo=utc)",
                {'import datetime', 'from django.utils.timezone import utc'},
            )
        )

    def test_serialize_fields(self):
        self.assertSerializedFieldEqual(models.CharField(max_length=255))
        self.assertSerializedResultEqual(
            models.CharField(max_length=255),
            ("models.CharField(max_length=255)", {"from django.db import models"})
        )
        self.assertSerializedFieldEqual(models.TextField(null=True, blank=True))
        self.assertSerializedResultEqual(
            models.TextField(null=True, blank=True),
            ("models.TextField(blank=True, null=True)", {'from django.db import models'})
        )

    def test_serialize_settings(self):
        self.assertSerializedEqual(SettingsReference(settings.AUTH_USER_MODEL, "AUTH_USER_MODEL"))
        self.assertSerializedResultEqual(
            SettingsReference("someapp.model", "AUTH_USER_MODEL"),
            ("settings.AUTH_USER_MODEL", {"from django.conf import settings"})
        )

    def test_serialize_iterators(self):
        self.assertSerializedResultEqual(
            ((x, x * x) for x in range(3)),
            ("((0, 0), (1, 1), (2, 4))", set())
        )

    def test_serialize_compiled_regex(self):
        """
        Make sure compiled regex can be serialized.
        """
        regex = re.compile(r'^\w+$')
        self.assertSerializedEqual(regex)

    def test_serialize_class_based_validators(self):
        """
        Ticket #22943: Test serialization of class-based validators, including
        compiled regexes.
        """
        validator = RegexValidator(message="hello")
        string = MigrationWriter.serialize(validator)[0]
        self.assertEqual(string, "django.core.validators.RegexValidator(message='hello')")
        self.serialize_round_trip(validator)

        # Test with a compiled regex.
        validator = RegexValidator(regex=re.compile(r'^\w+$'))
        string = MigrationWriter.serialize(validator)[0]
        self.assertEqual(string, "django.core.validators.RegexValidator(regex=re.compile('^\\\\w+$'))")
        self.serialize_round_trip(validator)

        # Test a string regex with flag
        validator = RegexValidator(r'^[0-9]+$', flags=re.S)
        string = MigrationWriter.serialize(validator)[0]
        self.assertEqual(string, "django.core.validators.RegexValidator('^[0-9]+$', flags=re.RegexFlag['DOTALL'])")
        self.serialize_round_trip(validator)

        # Test message and code
        validator = RegexValidator('^[-a-zA-Z0-9_]+$', 'Invalid', 'invalid')
        string = MigrationWriter.serialize(validator)[0]
        self.assertEqual(string, "django.core.validators.RegexValidator('^[-a-zA-Z0-9_]+$', 'Invalid', 'invalid')")
        self.serialize_round_trip(validator)

        # Test with a subclass.
        validator = EmailValidator(message="hello")
        string = MigrationWriter.serialize(validator)[0]
        self.assertEqual(string, "django.core.validators.EmailValidator(message='hello')")
        self.serialize_round_trip(validator)

        validator = deconstructible(path="migrations.test_writer.EmailValidator")(EmailValidator)(message="hello")
        string = MigrationWriter.serialize(validator)[0]
        self.assertEqual(string, "migrations.test_writer.EmailValidator(message='hello')")

        validator = deconstructible(path="custom.EmailValidator")(EmailValidator)(message="hello")
        with self.assertRaisesMessage(ImportError, "No module named 'custom'"):
            MigrationWriter.serialize(validator)

        validator = deconstructible(path="django.core.validators.EmailValidator2")(EmailValidator)(message="hello")
        with self.assertRaisesMessage(ValueError, "Could not find object EmailValidator2 in django.core.validators."):
            MigrationWriter.serialize(validator)

    def test_serialize_empty_nonempty_tuple(self):
        """
        Ticket #22679: makemigrations generates invalid code for (an empty
        tuple) default_permissions = ()
        """
        empty_tuple = ()
        one_item_tuple = ('a',)
        many_items_tuple = ('a', 'b', 'c')
        self.assertSerializedEqual(empty_tuple)
        self.assertSerializedEqual(one_item_tuple)
        self.assertSerializedEqual(many_items_tuple)

    def test_serialize_range(self):
        string, imports = MigrationWriter.serialize(range(1, 5))
        self.assertEqual(string, 'range(1, 5)')
        self.assertEqual(imports, set())

    def test_serialize_builtins(self):
        string, imports = MigrationWriter.serialize(range)
        self.assertEqual(string, 'range')
        self.assertEqual(imports, set())

    def test_serialize_unbound_method_reference(self):
        """An unbound method used within a class body can be serialized."""
        self.serialize_round_trip(TestModel1.thing)

    def test_serialize_local_function_reference(self):
        """A reference in a local scope can't be serialized."""
        class TestModel2:
            def upload_to(self):
                return "somewhere dynamic"
            thing = models.FileField(upload_to=upload_to)

        with self.assertRaisesMessage(ValueError, 'Could not find function upload_to in migrations.test_writer'):
            self.serialize_round_trip(TestModel2.thing)

    def test_serialize_managers(self):
        self.assertSerializedEqual(models.Manager())
        self.assertSerializedResultEqual(
            FoodQuerySet.as_manager(),
            ('migrations.models.FoodQuerySet.as_manager()', {'import migrations.models'})
        )
        self.assertSerializedEqual(FoodManager('a', 'b'))
        self.assertSerializedEqual(FoodManager('x', 'y', c=3, d=4))

    def test_serialize_frozensets(self):
        self.assertSerializedEqual(frozenset())
        self.assertSerializedEqual(frozenset("let it go"))

    def test_serialize_set(self):
        self.assertSerializedEqual(set())
        self.assertSerializedResultEqual(set(), ('set()', set()))
        self.assertSerializedEqual({'a'})
        self.assertSerializedResultEqual({'a'}, ("{'a'}", set()))

    def test_serialize_timedelta(self):
        self.assertSerializedEqual(datetime.timedelta())
        self.assertSerializedEqual(datetime.timedelta(minutes=42))

    def test_serialize_functools_partial(self):
        value = functools.partial(datetime.timedelta, 1, seconds=2)
        result = self.serialize_round_trip(value)
        self.assertEqual(result.func, value.func)
        self.assertEqual(result.args, value.args)
        self.assertEqual(result.keywords, value.keywords)

    def test_serialize_functools_partialmethod(self):
        value = functools.partialmethod(datetime.timedelta, 1, seconds=2)
        result = self.serialize_round_trip(value)
        self.assertIsInstance(result, functools.partialmethod)
        self.assertEqual(result.func, value.func)
        self.assertEqual(result.args, value.args)
        self.assertEqual(result.keywords, value.keywords)

    def test_serialize_type_none(self):
        self.assertSerializedEqual(type(None))

    def test_simple_migration(self):
        """
        Tests serializing a simple migration.
        """
        fields = {
            'charfield': models.DateTimeField(default=datetime.datetime.utcnow),
            'datetimefield': models.DateTimeField(default=datetime.datetime.utcnow),
        }

        options = {
            'verbose_name': 'My model',
            'verbose_name_plural': 'My models',
        }

        migration = type("Migration", (migrations.Migration,), {
            "operations": [
                migrations.CreateModel("MyModel", tuple(fields.items()), options, (models.Model,)),
                migrations.CreateModel("MyModel2", tuple(fields.items()), bases=(models.Model,)),
                migrations.CreateModel(
                    name="MyModel3", fields=tuple(fields.items()), options=options, bases=(models.Model,)
                ),
                migrations.DeleteModel("MyModel"),
                migrations.AddField("OtherModel", "datetimefield", fields["datetimefield"]),
            ],
            "dependencies": [("testapp", "some_other_one")],
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        # We don't test the output formatting - that's too fragile.
        # Just make sure it runs for now, and that things look alright.
        result = self.safe_exec(output)
        self.assertIn("Migration", result)

    def test_migration_path(self):
        test_apps = [
            'migrations.migrations_test_apps.normal',
            'migrations.migrations_test_apps.with_package_model',
            'migrations.migrations_test_apps.without_init_file',
        ]

        base_dir = os.path.dirname(os.path.dirname(__file__))

        for app in test_apps:
            with self.modify_settings(INSTALLED_APPS={'append': app}):
                migration = migrations.Migration('0001_initial', app.split('.')[-1])
                expected_path = os.path.join(base_dir, *(app.split('.') + ['migrations', '0001_initial.py']))
                writer = MigrationWriter(migration)
                self.assertEqual(writer.path, expected_path)

    def test_custom_operation(self):
        migration = type("Migration", (migrations.Migration,), {
            "operations": [
                custom_migration_operations.operations.TestOperation(),
                custom_migration_operations.operations.CreateModel(),
                migrations.CreateModel("MyModel", (), {}, (models.Model,)),
                custom_migration_operations.more_operations.TestOperation()
            ],
            "dependencies": []
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        result = self.safe_exec(output)
        self.assertIn("custom_migration_operations", result)
        self.assertNotEqual(
            result['custom_migration_operations'].operations.TestOperation,
            result['custom_migration_operations'].more_operations.TestOperation
        )

    def test_sorted_imports(self):
        """
        #24155 - Tests ordering of imports.
        """
        migration = type("Migration", (migrations.Migration,), {
            "operations": [
                migrations.AddField("mymodel", "myfield", models.DateTimeField(
                    default=datetime.datetime(2012, 1, 1, 1, 1, tzinfo=utc),
                )),
            ]
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        self.assertIn(
            "import datetime\n"
            "from django.db import migrations, models\n"
            "from django.utils.timezone import utc\n",
            output
        )

    def test_migration_file_header_comments(self):
        """
        Test comments at top of file.
        """
        migration = type("Migration", (migrations.Migration,), {
            "operations": []
        })
        dt = datetime.datetime(2015, 7, 31, 4, 40, 0, 0, tzinfo=utc)
        with mock.patch('django.db.migrations.writer.now', lambda: dt):
            for include_header in (True, False):
                with self.subTest(include_header=include_header):
                    writer = MigrationWriter(migration, include_header)
                    output = writer.as_string()

                    self.assertEqual(
                        include_header,
                        output.startswith(
                            "# Generated by Django %s on 2015-07-31 04:40\n\n" % get_version()
                        )
                    )
                    if not include_header:
                        # Make sure the output starts with something that's not
                        # a comment or indentation or blank line
                        self.assertRegex(output.splitlines(keepends=True)[0], r"^[^#\s]+")

    def test_models_import_omitted(self):
        """
        django.db.models shouldn't be imported if unused.
        """
        migration = type("Migration", (migrations.Migration,), {
            "operations": [
                migrations.AlterModelOptions(
                    name='model',
                    options={'verbose_name': 'model', 'verbose_name_plural': 'models'},
                ),
            ]
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        self.assertIn("from django.db import migrations\n", output)

    def test_deconstruct_class_arguments(self):
        # Yes, it doesn't make sense to use a class as a default for a
        # CharField. It does make sense for custom fields though, for example
        # an enumfield that takes the enum class as an argument.
        string = MigrationWriter.serialize(models.CharField(default=DeconstructibleInstances))[0]
        self.assertEqual(string, "models.CharField(default=migrations.test_writer.DeconstructibleInstances)")

    def test_register_serializer(self):
        class ComplexSerializer(BaseSerializer):
            def serialize(self):
                return 'complex(%r)' % self.value, {}

        MigrationWriter.register_serializer(complex, ComplexSerializer)
        self.assertSerializedEqual(complex(1, 2))
        MigrationWriter.unregister_serializer(complex)
        with self.assertRaisesMessage(ValueError, 'Cannot serialize: (1+2j)'):
            self.assertSerializedEqual(complex(1, 2))

    def test_register_non_serializer(self):
        with self.assertRaisesMessage(ValueError, "'TestModel1' must inherit from 'BaseSerializer'."):
            MigrationWriter.register_serializer(complex, TestModel1)
