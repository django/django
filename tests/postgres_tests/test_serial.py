from django.core.exceptions import ValidationError
from django.core.management.color import no_style
from django.db import connection, models
from django.test.utils import isolate_apps

from . import PostgreSQLTestCase
from .fields import BigSerialField, SerialField, SmallSerialField
from .models import SerialFKModel, SerialModel, SerialPKModel


@isolate_apps("postgres_tests")
class SerialFieldTests(PostgreSQLTestCase):
    def test_blank_unsupported(self):
        with self.assertRaisesMessage(ValueError, "SerialField must be blank."):
            SerialField(blank=False)

    def test_null_unsupported(self):
        with self.assertRaisesMessage(ValueError, "SerialField must not be null."):
            SerialField(null=True)

    def test_default_unsupported(self):
        with self.assertRaisesMessage(ValueError, "SerialField cannot have a default."):
            SerialField(default=1)

    def test_db_default_unsupported(self):
        with self.assertRaisesMessage(
            ValueError, "SerialField cannot have a database default."
        ):
            SerialField(db_default=1)

    def test_db_types(self):
        class Foo(models.Model):
            small_serial = SmallSerialField()
            serial = SerialField()
            big_serial = BigSerialField()

        small_serial = Foo._meta.get_field("small_serial")
        serial = Foo._meta.get_field("serial")
        big_serial = Foo._meta.get_field("big_serial")

        self.assertEqual(small_serial.db_type(connection), "smallserial")
        self.assertEqual(serial.db_type(connection), "serial")
        self.assertEqual(big_serial.db_type(connection), "bigserial")

        self.assertEqual(small_serial.cast_db_type(connection), "smallint")
        self.assertEqual(serial.cast_db_type(connection), "integer")
        self.assertEqual(big_serial.cast_db_type(connection), "bigint")

    def test_rel_db_types(self):
        class SerialPK(models.Model):
            id = SerialField(primary_key=True)

        class SmallSerialPK(models.Model):
            id = SmallSerialField(primary_key=True)

        class BigSerialPK(models.Model):
            id = BigSerialField(primary_key=True)

        class SerialFK(models.Model):
            fk = models.ForeignKey(SerialPK, on_delete=models.CASCADE)

        class SmallSerialFK(models.Model):
            fk = models.ForeignKey(SmallSerialPK, on_delete=models.CASCADE)

        class BigSerialFK(models.Model):
            fk = models.ForeignKey(BigSerialPK, on_delete=models.CASCADE)

        fk = SerialFK._meta.get_field("fk")
        small_fk = SmallSerialFK._meta.get_field("fk")
        big_fk = BigSerialFK._meta.get_field("fk")

        self.assertEqual(fk.rel_db_type(connection), "integer")
        self.assertEqual(small_fk.rel_db_type(connection), "smallint")
        self.assertEqual(big_fk.rel_db_type(connection), "bigint")


class SerialModelBaseTests(PostgreSQLTestCase):
    @classmethod
    def reset_sequences_to_1(cls, model):
        with connection.cursor() as cursor:
            for statement in cls.get_sequence_reset_by_name_sql(model):
                cursor.execute(statement)

    @classmethod
    def get_sequence_reset_by_name_sql(cls, model):
        return connection.ops.sequence_reset_by_name_sql(
            no_style(), cls.get_sequences(model)
        )

    @classmethod
    def get_sequences(cls, model):
        with connection.cursor() as cursor:
            return connection.introspection.get_sequences(cursor, model._meta.db_table)

    @classmethod
    def reset_sequences_to_max(cls, model):
        with connection.cursor() as cursor:
            for statement in cls.get_sequence_reset_sql(model):
                cursor.execute(statement)

    @classmethod
    def get_sequence_reset_sql(cls, model):
        return connection.ops.sequence_reset_sql(no_style(), [model])

    @classmethod
    def get_table_description(cls, model):
        with connection.cursor() as cursor:
            return connection.introspection.get_table_description(
                cursor, model._meta.db_table
            )


class SerialModelTests(SerialModelBaseTests):
    def test_create(self):
        self.reset_sequences_to_1(SerialModel)

        # The serial fields start from 1.
        obj_1 = SerialModel.objects.create()
        self.assertEqual(obj_1.small_serial, 1)
        self.assertEqual(obj_1.serial, 1)
        self.assertEqual(obj_1.big_serial, 1)

        # The serial fields are incremented by 1 if not provided.
        obj_2 = SerialModel.objects.create()
        self.assertEqual(obj_2.small_serial, 2)
        self.assertEqual(obj_2.serial, 2)
        self.assertEqual(obj_2.big_serial, 2)

        # The serial fields are incremented by 1 if set to None.
        obj_3 = SerialModel.objects.create(
            small_serial=None,
            serial=None,
            big_serial=None,
        )
        self.assertEqual(obj_3.small_serial, 3)
        self.assertEqual(obj_3.serial, 3)
        self.assertEqual(obj_3.big_serial, 3)

        # It's possible to provide values for serial fields.
        obj_4 = SerialModel.objects.create(
            small_serial=111,
            serial=222,
            big_serial=333,
        )
        self.assertEqual(obj_4.small_serial, 111)
        self.assertEqual(obj_4.serial, 222)
        self.assertEqual(obj_4.big_serial, 333)

        # The sequence was not interrupted.
        obj_5 = SerialModel.objects.create()
        self.assertEqual(obj_5.small_serial, 4)
        self.assertEqual(obj_5.serial, 4)
        self.assertEqual(obj_5.big_serial, 4)

        # The serial fields don't need to be unique.
        obj_6 = SerialModel.objects.create(
            small_serial=1,
            serial=1,
            big_serial=1,
        )
        self.assertEqual(obj_6.small_serial, 1)
        self.assertEqual(obj_6.serial, 1)
        self.assertEqual(obj_6.big_serial, 1)

        # The sequence was not interrupted.
        obj_7 = SerialModel.objects.create()
        self.assertEqual(obj_7.small_serial, 5)
        self.assertEqual(obj_7.serial, 5)
        self.assertEqual(obj_7.big_serial, 5)

    def test_full_clean_success(self):
        small_lo, small_hi = (-32768, 32767)
        lo, hi = (-2147483648, 2147483647)
        big_lo, big_hi = (-9223372036854775808, 9223372036854775807)
        test_cases = (
            {},
            {"small_serial": None},
            {"serial": None},
            {"big_serial": None},
            {"small_serial": small_lo},
            {"small_serial": small_hi},
            {"serial": lo},
            {"serial": hi},
            {"big_serial": big_lo},
            {"big_serial": big_hi},
        )

        for kwargs in test_cases:
            with self.subTest(kwargs=kwargs):
                self.assertIsNone(SerialModel(**kwargs).full_clean())

    def test_full_clean_failure(self):
        small_lo, small_hi = (-32768, 32767)
        lo, hi = (-2147483648, 2147483647)
        big_lo, big_hi = (-9223372036854775808, 9223372036854775807)
        lte = "Ensure this value is less than or equal to %s."
        gte = "Ensure this value is greater than or equal to %s."
        test_cases = (
            ({"small_serial": small_hi + 1}, [lte % small_hi]),
            ({"serial": hi + 1}, [lte % hi]),
            ({"big_serial": big_hi + 1}, [lte % big_hi]),
            ({"small_serial": small_lo - 1}, [gte % small_lo]),
            ({"serial": lo - 1}, [gte % lo]),
            ({"big_serial": big_lo - 1}, [gte % big_lo]),
        )

        for kwargs, messages in test_cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError) as ctx:
                    SerialModel(**kwargs).full_clean()

                self.assertSequenceEqual(ctx.exception.messages, messages)

    def test_get_sequences(self):
        sequences = self.get_sequences(SerialModel)

        table = SerialModel._meta.db_table
        self.assertEqual(len(sequences), 4)
        self.assertEqual(sequences[0]["column"], "id")
        self.assertEqual(sequences[0]["name"], f"{table}_id_seq")
        self.assertEqual(sequences[0]["table"], table)
        self.assertEqual(sequences[1]["column"], "small_serial")
        self.assertEqual(sequences[1]["name"], f"{table}_small_serial_seq")
        self.assertEqual(sequences[1]["table"], table)
        self.assertEqual(sequences[2]["column"], "serial")
        self.assertEqual(sequences[2]["name"], f"{table}_serial_seq")
        self.assertEqual(sequences[2]["table"], table)
        self.assertEqual(sequences[3]["column"], "big_serial")
        self.assertEqual(sequences[3]["name"], f"{table}_big_serial_seq")
        self.assertEqual(sequences[3]["table"], table)

    def test_get_sequence_reset_sql(self):
        def get_statement(field):
            db_table = SerialModel._meta.db_table
            return (
                f"SELECT setval("
                f"pg_get_serial_sequence('\"{db_table}\"','{field}'), "
                f'coalesce(max("{field}"), 1), '
                f'max("{field}") IS NOT null'
                f') FROM "{db_table}";'
            )

        statements = self.get_sequence_reset_sql(SerialModel)
        self.assertEqual(len(statements), 4)
        self.assertEqual(statements[0], get_statement("id"))
        self.assertEqual(statements[1], get_statement("small_serial"))
        self.assertEqual(statements[2], get_statement("serial"))
        self.assertEqual(statements[3], get_statement("big_serial"))

    def test_reset_sequences_to_max_if_record_exists(self):
        obj_1 = SerialModel.objects.create(small_serial=1, serial=2, big_serial=3)
        self.assertEqual(obj_1.small_serial, 1)
        self.assertEqual(obj_1.serial, 2)
        self.assertEqual(obj_1.big_serial, 3)

        self.reset_sequences_to_max(SerialModel)

        obj_2 = SerialModel.objects.create()
        self.assertEqual(obj_2.small_serial, 2)
        self.assertEqual(obj_2.serial, 3)
        self.assertEqual(obj_2.big_serial, 4)

        obj_3 = SerialModel.objects.create()
        self.assertEqual(obj_3.small_serial, 3)
        self.assertEqual(obj_3.serial, 4)
        self.assertEqual(obj_3.big_serial, 5)

    def test_reset_sequences_to_max_if_record_doesnt_exist(self):
        self.reset_sequences_to_max(SerialModel)

        obj_1 = SerialModel.objects.create()
        self.assertEqual(obj_1.small_serial, 1)
        self.assertEqual(obj_1.serial, 1)
        self.assertEqual(obj_1.big_serial, 1)

        obj_2 = SerialModel.objects.create()
        self.assertEqual(obj_2.small_serial, 2)
        self.assertEqual(obj_2.serial, 2)
        self.assertEqual(obj_2.big_serial, 2)

    def test_bulk_create(self):
        self.reset_sequences_to_1(SerialModel)
        objs = [
            SerialModel(),
            SerialModel(small_serial=1, serial=1, big_serial=1),
            SerialModel(serial=5),
            SerialModel(),
        ]

        obj_1, obj_2, obj_3, obj_4 = SerialModel.objects.bulk_create(objs)
        self.assertEqual(
            (obj_1.small_serial, obj_1.serial, obj_1.big_serial),
            (1, 1, 1),
        )
        self.assertEqual(
            (obj_2.small_serial, obj_2.serial, obj_2.big_serial),
            (1, 1, 1),
        )
        self.assertEqual(
            (obj_3.small_serial, obj_3.serial, obj_3.big_serial),
            (2, 5, 2),
        )
        self.assertEqual(
            (obj_4.small_serial, obj_4.serial, obj_4.big_serial),
            (3, 2, 3),
        )


class SerialFKModelTests(SerialModelBaseTests):
    def test_create(self):
        self.reset_sequences_to_1(SerialPKModel)
        self.reset_sequences_to_1(SerialFKModel)

        obj_1 = SerialPKModel.objects.create()
        self.assertEqual(obj_1.id, 1)

        obj_2 = SerialPKModel.objects.create()
        self.assertEqual(obj_2.id, 2)

        obj_3 = SerialFKModel.objects.create(fk=obj_2)
        self.assertEqual(obj_3.id, 1)
        self.assertEqual(obj_3.fk, obj_2)
        self.assertEqual(obj_3.fk_id, obj_2.id)

        columns = self.get_table_description(SerialFKModel)
        fk_id = columns[1]
        self.assertEqual(fk_id.name, "fk_id")
        self.assertEqual(fk_id.type_code, 23)  # IntegerField.
        self.assertEqual(fk_id.internal_size, 4)
        self.assertIsNone(fk_id.default)
