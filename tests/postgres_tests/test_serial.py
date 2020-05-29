import warnings

from django.core.exceptions import ImproperlyConfigured
from django.core.management.color import no_style
from django.db import IntegrityError, connection, models
from django.test.utils import isolate_apps

from . import PostgreSQLTestCase, PostgreSQLTransactionTestCase
from .fields import BigSerialField, SerialField, SmallSerialField
from .models import SerialModel

try:
    from django.db.backends.postgresql.base import DatabaseWrapper
except ImproperlyConfigured:
    from django.db.backends.dummy.base import DatabaseWrapper


@isolate_apps('invalid_models_tests')
class SerialFieldModelTests(PostgreSQLTestCase):
    def test_not_null(self):
        class Model(models.Model):
            id = SerialField(null=True)

        field = Model._meta.get_field('id')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)
        self.assertFalse(field.null)

    def test_primary_key(self):
        class Model(models.Model):
            another = SerialField()

        field = Model._meta.get_field('id')
        errors = field.check()
        expected = []
        self.assertEqual(errors, expected)

    def test_internal_type(self):
        class Model(models.Model):
            small = SmallSerialField()
            regular = SerialField()
            big = BigSerialField(primary_key=False)

        small = Model._meta.get_field('small')
        regular = Model._meta.get_field('regular')
        big = Model._meta.get_field('big')

        self.assertIn(regular.get_internal_type(), DatabaseWrapper.data_types)
        self.assertIn(small.get_internal_type(), DatabaseWrapper.data_types)
        self.assertIn(big.get_internal_type(), DatabaseWrapper.data_types)

        self.assertEqual(DatabaseWrapper.data_types[regular.get_internal_type()], 'serial')
        self.assertEqual(DatabaseWrapper.data_types[small.get_internal_type()], 'smallserial')
        self.assertEqual(DatabaseWrapper.data_types[big.get_internal_type()], 'bigserial')


@isolate_apps('postgres_tests')
class SerialFieldSchemaTests(PostgreSQLTransactionTestCase):
    available_apps = ['postgres_tests']

    def test_serial_to_integer(self):
        class TestModel(models.Model):
            serial = SerialField()

        try:
            with connection.schema_editor() as editor:
                editor.create_model(TestModel)
            old_field = TestModel._meta.get_field('serial')
            TestModel.objects.create()

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    'ignore', category=RuntimeWarning,
                    message="Model 'postgres_tests.testmodel' was already registered."
                )

                class TestModel(models.Model):
                    serial = models.IntegerField()

            new_field = TestModel._meta.get_field('serial')
            with connection.schema_editor() as editor:
                editor.alter_field(TestModel, old_field, new_field, strict=True)

            with self.assertRaises(IntegrityError):
                TestModel.objects.create()
            TestModel.objects.create(serial=7)
        finally:
            with connection.schema_editor() as editor:
                editor.delete_model(TestModel)

    def test_int_pk_to_serial_pk(self):
        class TestModel(models.Model):
            id = models.IntegerField(unique=True, primary_key=True)

        try:
            with connection.schema_editor() as editor:
                editor.create_model(TestModel)
            with self.assertRaises(IntegrityError):
                TestModel.objects.create()
            old_field = TestModel._meta.get_field('id')

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    'ignore', category=RuntimeWarning,
                    message="Model 'postgres_tests.testmodel' was already registered."
                )

                class TestModel(models.Model):
                    id = SerialField(unique=True, primary_key=True)

            new_field = TestModel._meta.get_field('id')
            with connection.schema_editor() as editor:
                editor.alter_field(TestModel, old_field, new_field, strict=True)
            with connection.cursor() as cursor:
                for command in connection.ops.sequence_reset_sql(no_style(), [TestModel]):
                    cursor.execute(command)

            TestModel.objects.create()
        finally:
            with connection.schema_editor() as editor:
                editor.delete_model(TestModel)

    def test_implicit_id_to_serial(self):
        class TestModel(models.Model):
            pass

        try:
            with connection.schema_editor() as editor:
                editor.create_model(TestModel)
            old_field = TestModel._meta.get_field('id')
            TestModel.objects.create()

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    'ignore', category=RuntimeWarning,
                    message="Model 'postgres_tests.testmodel' was already registered."
                )

                class TestModel(models.Model):
                    id = SerialField(unique=True, primary_key=True)

            new_field = TestModel._meta.get_field('id')
            with connection.schema_editor() as editor:
                editor.alter_field(TestModel, old_field, new_field, strict=True)

            TestModel.objects.create()
        finally:
            with connection.schema_editor() as editor:
                editor.delete_model(TestModel)


class SerialFieldTests(PostgreSQLTestCase):
    def test_not_null(self):
        o = SerialModel.objects.create()
        self.assertIsNotNone(o.small)
        self.assertIsNotNone(o.big)

    def test_auto_increment(self):
        o1 = SerialModel.objects.create()
        o2 = SerialModel.objects.create()
        self.assertGreater(o2.regular, o1.regular)
        self.assertGreater(o2.small, o1.small)
        self.assertGreater(o2.big, o1.big)

    def test_sequnece_ops(self):
        with connection.cursor() as cursor:
            sequences = [
                seq for seq in connection.introspection.get_sequences(cursor, SerialModel._meta.db_table)
                if seq['column'] == 'regular'
            ]
            for command in connection.ops.sequence_reset_by_name_sql(no_style(), sequences):
                cursor.execute(command)
        for i in range(1, 6, 2):
            self.assertEqual(SerialModel.objects.create(regular=i).regular, i)
        for i in range(1, 3):
            self.assertEqual(SerialModel.objects.create().regular, i)
        with connection.cursor() as cursor:
            for command in connection.ops.sequence_reset_sql(no_style(), [SerialModel]):
                cursor.execute(command)
        self.assertEqual(SerialModel.objects.create().regular, 6)
        with connection.cursor() as cursor:
            sequences = [
                seq for seq in connection.introspection.get_sequences(cursor, SerialModel._meta.db_table)
                if seq['column'] == 'regular'
            ]
            for command in connection.ops.sequence_reset_by_name_sql(no_style(), sequences):
                cursor.execute(command)
        self.assertEqual(SerialModel.objects.create().regular, 1)
