import datetime
from unittest import mock

from django.contrib.postgres.indexes import OpClass
from django.core.exceptions import ValidationError
from django.db import IntegrityError, NotSupportedError, connection, transaction
from django.db.models import (
    CheckConstraint,
    Deferrable,
    F,
    Func,
    IntegerField,
    Model,
    Q,
    UniqueConstraint,
)
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Left, Lower
from django.test import ignore_warnings, modify_settings, skipUnlessDBFeature
from django.test.utils import isolate_apps
from django.utils import timezone
from django.utils.deprecation import RemovedInDjango50Warning

from . import PostgreSQLTestCase
from .models import HotelReservation, IntegerArrayModel, RangesModel, Room, Scene

try:
    from psycopg2.extras import DateRange, NumericRange

    from django.contrib.postgres.constraints import ExclusionConstraint
    from django.contrib.postgres.fields import (
        DateTimeRangeField,
        RangeBoundary,
        RangeOperators,
    )
except ImportError:
    pass


@modify_settings(INSTALLED_APPS={"append": "django.contrib.postgres"})
class SchemaTests(PostgreSQLTestCase):
    get_opclass_query = """
        SELECT opcname, c.relname FROM pg_opclass AS oc
        JOIN pg_index as i on oc.oid = ANY(i.indclass)
        JOIN pg_class as c on c.oid = i.indexrelid
        WHERE c.relname = %s
    """

    def get_constraints(self, table):
        """Get the constraints on the table using a new cursor."""
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_check_constraint_range_value(self):
        constraint_name = "ints_between"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = CheckConstraint(
            check=Q(ints__contained_by=NumericRange(10, 30)),
            name=constraint_name,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(ints=(20, 50))
        RangesModel.objects.create(ints=(10, 30))

    def test_check_constraint_array_contains(self):
        constraint = CheckConstraint(
            check=Q(field__contains=[1]),
            name="array_contains",
        )
        msg = f"Constraint “{constraint.name}” is violated."
        with self.assertRaisesMessage(ValidationError, msg):
            constraint.validate(IntegerArrayModel, IntegerArrayModel())
        constraint.validate(IntegerArrayModel, IntegerArrayModel(field=[1]))

    def test_check_constraint_daterange_contains(self):
        constraint_name = "dates_contains"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = CheckConstraint(
            check=Q(dates__contains=F("dates_inner")),
            name=constraint_name,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        date_1 = datetime.date(2016, 1, 1)
        date_2 = datetime.date(2016, 1, 4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(
                dates=(date_1, date_2),
                dates_inner=(date_1, date_2.replace(day=5)),
            )
        RangesModel.objects.create(
            dates=(date_1, date_2),
            dates_inner=(date_1, date_2),
        )

    def test_check_constraint_datetimerange_contains(self):
        constraint_name = "timestamps_contains"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = CheckConstraint(
            check=Q(timestamps__contains=F("timestamps_inner")),
            name=constraint_name,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        datetime_1 = datetime.datetime(2016, 1, 1)
        datetime_2 = datetime.datetime(2016, 1, 2, 12)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(
                timestamps=(datetime_1, datetime_2),
                timestamps_inner=(datetime_1, datetime_2.replace(hour=13)),
            )
        RangesModel.objects.create(
            timestamps=(datetime_1, datetime_2),
            timestamps_inner=(datetime_1, datetime_2),
        )

    def test_check_constraint_range_contains(self):
        constraint = CheckConstraint(
            check=Q(ints__contains=(1, 5)),
            name="ints_contains",
        )
        msg = f"Constraint “{constraint.name}” is violated."
        with self.assertRaisesMessage(ValidationError, msg):
            constraint.validate(RangesModel, RangesModel(ints=(6, 10)))

    def test_check_constraint_range_lower_upper(self):
        constraint = CheckConstraint(
            check=Q(ints__startswith__gte=0) & Q(ints__endswith__lte=99),
            name="ints_range_lower_upper",
        )
        msg = f"Constraint “{constraint.name}” is violated."
        with self.assertRaisesMessage(ValidationError, msg):
            constraint.validate(RangesModel, RangesModel(ints=(-1, 20)))
        with self.assertRaisesMessage(ValidationError, msg):
            constraint.validate(RangesModel, RangesModel(ints=(0, 100)))
        constraint.validate(RangesModel, RangesModel(ints=(0, 99)))

    def test_check_constraint_range_lower_with_nulls(self):
        constraint = CheckConstraint(
            check=Q(ints__isnull=True) | Q(ints__startswith__gte=0),
            name="ints_optional_positive_range",
        )
        constraint.validate(RangesModel, RangesModel())
        constraint = CheckConstraint(
            check=Q(ints__startswith__gte=0),
            name="ints_positive_range",
        )
        msg = f"Constraint “{constraint.name}” is violated."
        with self.assertRaisesMessage(ValidationError, msg):
            constraint.validate(RangesModel, RangesModel())

    def test_opclass(self):
        constraint = UniqueConstraint(
            name="test_opclass",
            fields=["scene"],
            opclasses=["varchar_pattern_ops"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(Scene, constraint)
        self.assertIn(constraint.name, self.get_constraints(Scene._meta.db_table))
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [constraint.name])
            self.assertEqual(
                cursor.fetchall(),
                [("varchar_pattern_ops", constraint.name)],
            )
        # Drop the constraint.
        with connection.schema_editor() as editor:
            editor.remove_constraint(Scene, constraint)
        self.assertNotIn(constraint.name, self.get_constraints(Scene._meta.db_table))

    def test_opclass_multiple_columns(self):
        constraint = UniqueConstraint(
            name="test_opclass_multiple",
            fields=["scene", "setting"],
            opclasses=["varchar_pattern_ops", "text_pattern_ops"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(Scene, constraint)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [constraint.name])
            expected_opclasses = (
                ("varchar_pattern_ops", constraint.name),
                ("text_pattern_ops", constraint.name),
            )
            self.assertCountEqual(cursor.fetchall(), expected_opclasses)

    def test_opclass_partial(self):
        constraint = UniqueConstraint(
            name="test_opclass_partial",
            fields=["scene"],
            opclasses=["varchar_pattern_ops"],
            condition=Q(setting__contains="Sir Bedemir's Castle"),
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(Scene, constraint)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [constraint.name])
            self.assertCountEqual(
                cursor.fetchall(),
                [("varchar_pattern_ops", constraint.name)],
            )

    @skipUnlessDBFeature("supports_covering_indexes")
    def test_opclass_include(self):
        constraint = UniqueConstraint(
            name="test_opclass_include",
            fields=["scene"],
            opclasses=["varchar_pattern_ops"],
            include=["setting"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(Scene, constraint)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [constraint.name])
            self.assertCountEqual(
                cursor.fetchall(),
                [("varchar_pattern_ops", constraint.name)],
            )

    @skipUnlessDBFeature("supports_expression_indexes")
    def test_opclass_func(self):
        constraint = UniqueConstraint(
            OpClass(Lower("scene"), name="text_pattern_ops"),
            name="test_opclass_func",
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(Scene, constraint)
        constraints = self.get_constraints(Scene._meta.db_table)
        self.assertIs(constraints[constraint.name]["unique"], True)
        self.assertIn(constraint.name, constraints)
        with editor.connection.cursor() as cursor:
            cursor.execute(self.get_opclass_query, [constraint.name])
            self.assertEqual(
                cursor.fetchall(),
                [("text_pattern_ops", constraint.name)],
            )
        Scene.objects.create(scene="Scene 10", setting="The dark forest of Ewing")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Scene.objects.create(scene="ScEnE 10", setting="Sir Bedemir's Castle")
        Scene.objects.create(scene="Scene 5", setting="Sir Bedemir's Castle")
        # Drop the constraint.
        with connection.schema_editor() as editor:
            editor.remove_constraint(Scene, constraint)
        self.assertNotIn(constraint.name, self.get_constraints(Scene._meta.db_table))
        Scene.objects.create(scene="ScEnE 10", setting="Sir Bedemir's Castle")


@modify_settings(INSTALLED_APPS={"append": "django.contrib.postgres"})
class ExclusionConstraintTests(PostgreSQLTestCase):
    def get_constraints(self, table):
        """Get the constraints on the table using a new cursor."""
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_invalid_condition(self):
        msg = "ExclusionConstraint.condition must be a Q instance."
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                index_type="GIST",
                name="exclude_invalid_condition",
                expressions=[(F("datespan"), RangeOperators.OVERLAPS)],
                condition=F("invalid"),
            )

    def test_invalid_index_type(self):
        msg = "Exclusion constraints only support GiST or SP-GiST indexes."
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                index_type="gin",
                name="exclude_invalid_index_type",
                expressions=[(F("datespan"), RangeOperators.OVERLAPS)],
            )

    def test_invalid_expressions(self):
        msg = "The expressions must be a list of 2-tuples."
        for expressions in (["foo"], [("foo")], [("foo_1", "foo_2", "foo_3")]):
            with self.subTest(expressions), self.assertRaisesMessage(ValueError, msg):
                ExclusionConstraint(
                    index_type="GIST",
                    name="exclude_invalid_expressions",
                    expressions=expressions,
                )

    def test_empty_expressions(self):
        msg = "At least one expression is required to define an exclusion constraint."
        for empty_expressions in (None, []):
            with self.subTest(empty_expressions), self.assertRaisesMessage(
                ValueError, msg
            ):
                ExclusionConstraint(
                    index_type="GIST",
                    name="exclude_empty_expressions",
                    expressions=empty_expressions,
                )

    def test_invalid_deferrable(self):
        msg = "ExclusionConstraint.deferrable must be a Deferrable instance."
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                name="exclude_invalid_deferrable",
                expressions=[(F("datespan"), RangeOperators.OVERLAPS)],
                deferrable="invalid",
            )

    def test_deferrable_with_condition(self):
        msg = "ExclusionConstraint with conditions cannot be deferred."
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                name="exclude_invalid_condition",
                expressions=[(F("datespan"), RangeOperators.OVERLAPS)],
                condition=Q(cancelled=False),
                deferrable=Deferrable.DEFERRED,
            )

    def test_invalid_include_type(self):
        msg = "ExclusionConstraint.include must be a list or tuple."
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                name="exclude_invalid_include",
                expressions=[(F("datespan"), RangeOperators.OVERLAPS)],
                include="invalid",
            )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_invalid_opclasses_type(self):
        msg = "ExclusionConstraint.opclasses must be a list or tuple."
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                name="exclude_invalid_opclasses",
                expressions=[(F("datespan"), RangeOperators.OVERLAPS)],
                opclasses="invalid",
            )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_opclasses_and_expressions_same_length(self):
        msg = (
            "ExclusionConstraint.expressions and "
            "ExclusionConstraint.opclasses must have the same number of "
            "elements."
        )
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                name="exclude_invalid_expressions_opclasses_length",
                expressions=[(F("datespan"), RangeOperators.OVERLAPS)],
                opclasses=["foo", "bar"],
            )

    def test_repr(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                (F("datespan"), RangeOperators.OVERLAPS),
                (F("room"), RangeOperators.EQUAL),
            ],
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type='GIST' expressions=["
            "(F(datespan), '&&'), (F(room), '=')] name='exclude_overlapping'>",
        )
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[(F("datespan"), RangeOperators.ADJACENT_TO)],
            condition=Q(cancelled=False),
            index_type="SPGiST",
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type='SPGiST' expressions=["
            "(F(datespan), '-|-')] name='exclude_overlapping' "
            "condition=(AND: ('cancelled', False))>",
        )
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[(F("datespan"), RangeOperators.ADJACENT_TO)],
            deferrable=Deferrable.IMMEDIATE,
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type='GIST' expressions=["
            "(F(datespan), '-|-')] name='exclude_overlapping' "
            "deferrable=Deferrable.IMMEDIATE>",
        )
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[(F("datespan"), RangeOperators.ADJACENT_TO)],
            include=["cancelled", "room"],
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type='GIST' expressions=["
            "(F(datespan), '-|-')] name='exclude_overlapping' "
            "include=('cancelled', 'room')>",
        )
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                (OpClass("datespan", name="range_ops"), RangeOperators.ADJACENT_TO),
            ],
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type='GIST' expressions=["
            "(OpClass(F(datespan), name=range_ops), '-|-')] "
            "name='exclude_overlapping'>",
        )

    def test_eq(self):
        constraint_1 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                (F("datespan"), RangeOperators.OVERLAPS),
                (F("room"), RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
        )
        constraint_2 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
        )
        constraint_3 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[("datespan", RangeOperators.OVERLAPS)],
            condition=Q(cancelled=False),
        )
        constraint_4 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
            deferrable=Deferrable.DEFERRED,
        )
        constraint_5 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
            deferrable=Deferrable.IMMEDIATE,
        )
        constraint_6 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
            deferrable=Deferrable.IMMEDIATE,
            include=["cancelled"],
        )
        constraint_7 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
            include=["cancelled"],
        )
        with ignore_warnings(category=RemovedInDjango50Warning):
            constraint_8 = ExclusionConstraint(
                name="exclude_overlapping",
                expressions=[
                    ("datespan", RangeOperators.OVERLAPS),
                    ("room", RangeOperators.EQUAL),
                ],
                include=["cancelled"],
                opclasses=["range_ops", "range_ops"],
            )
            constraint_9 = ExclusionConstraint(
                name="exclude_overlapping",
                expressions=[
                    ("datespan", RangeOperators.OVERLAPS),
                    ("room", RangeOperators.EQUAL),
                ],
                opclasses=["range_ops", "range_ops"],
            )
            self.assertNotEqual(constraint_2, constraint_9)
            self.assertNotEqual(constraint_7, constraint_8)

        constraint_10 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                (F("datespan"), RangeOperators.OVERLAPS),
                (F("room"), RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
            violation_error_message="custom error",
        )
        constraint_11 = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                (F("datespan"), RangeOperators.OVERLAPS),
                (F("room"), RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
            violation_error_message="other custom error",
        )
        self.assertEqual(constraint_1, constraint_1)
        self.assertEqual(constraint_1, mock.ANY)
        self.assertNotEqual(constraint_1, constraint_2)
        self.assertNotEqual(constraint_1, constraint_3)
        self.assertNotEqual(constraint_1, constraint_4)
        self.assertNotEqual(constraint_1, constraint_10)
        self.assertNotEqual(constraint_2, constraint_3)
        self.assertNotEqual(constraint_2, constraint_4)
        self.assertNotEqual(constraint_2, constraint_7)
        self.assertNotEqual(constraint_4, constraint_5)
        self.assertNotEqual(constraint_5, constraint_6)
        self.assertNotEqual(constraint_1, object())
        self.assertNotEqual(constraint_10, constraint_11)
        self.assertEqual(constraint_10, constraint_10)

    def test_deconstruct(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(
            path, "django.contrib.postgres.constraints.ExclusionConstraint"
        )
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "exclude_overlapping",
                "expressions": [
                    ("datespan", RangeOperators.OVERLAPS),
                    ("room", RangeOperators.EQUAL),
                ],
            },
        )

    def test_deconstruct_index_type(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            index_type="SPGIST",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(
            path, "django.contrib.postgres.constraints.ExclusionConstraint"
        )
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "exclude_overlapping",
                "index_type": "SPGIST",
                "expressions": [
                    ("datespan", RangeOperators.OVERLAPS),
                    ("room", RangeOperators.EQUAL),
                ],
            },
        )

    def test_deconstruct_condition(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[
                ("datespan", RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(
            path, "django.contrib.postgres.constraints.ExclusionConstraint"
        )
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "exclude_overlapping",
                "expressions": [
                    ("datespan", RangeOperators.OVERLAPS),
                    ("room", RangeOperators.EQUAL),
                ],
                "condition": Q(cancelled=False),
            },
        )

    def test_deconstruct_deferrable(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[("datespan", RangeOperators.OVERLAPS)],
            deferrable=Deferrable.DEFERRED,
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(
            path, "django.contrib.postgres.constraints.ExclusionConstraint"
        )
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "exclude_overlapping",
                "expressions": [("datespan", RangeOperators.OVERLAPS)],
                "deferrable": Deferrable.DEFERRED,
            },
        )

    def test_deconstruct_include(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[("datespan", RangeOperators.OVERLAPS)],
            include=["cancelled", "room"],
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(
            path, "django.contrib.postgres.constraints.ExclusionConstraint"
        )
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "exclude_overlapping",
                "expressions": [("datespan", RangeOperators.OVERLAPS)],
                "include": ("cancelled", "room"),
            },
        )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_deconstruct_opclasses(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[("datespan", RangeOperators.OVERLAPS)],
            opclasses=["range_ops"],
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(
            path, "django.contrib.postgres.constraints.ExclusionConstraint"
        )
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs,
            {
                "name": "exclude_overlapping",
                "expressions": [("datespan", RangeOperators.OVERLAPS)],
                "opclasses": ["range_ops"],
            },
        )

    def _test_range_overlaps(self, constraint):
        # Create exclusion constraint.
        self.assertNotIn(
            constraint.name, self.get_constraints(HotelReservation._meta.db_table)
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(HotelReservation, constraint)
        self.assertIn(
            constraint.name, self.get_constraints(HotelReservation._meta.db_table)
        )
        # Add initial reservations.
        room101 = Room.objects.create(number=101)
        room102 = Room.objects.create(number=102)
        datetimes = [
            timezone.datetime(2018, 6, 20),
            timezone.datetime(2018, 6, 24),
            timezone.datetime(2018, 6, 26),
            timezone.datetime(2018, 6, 28),
            timezone.datetime(2018, 6, 29),
        ]
        reservation = HotelReservation.objects.create(
            datespan=DateRange(datetimes[0].date(), datetimes[1].date()),
            start=datetimes[0],
            end=datetimes[1],
            room=room102,
        )
        constraint.validate(HotelReservation, reservation)
        HotelReservation.objects.create(
            datespan=DateRange(datetimes[1].date(), datetimes[3].date()),
            start=datetimes[1],
            end=datetimes[3],
            room=room102,
        )
        HotelReservation.objects.create(
            datespan=DateRange(datetimes[3].date(), datetimes[4].date()),
            start=datetimes[3],
            end=datetimes[4],
            room=room102,
            cancelled=True,
        )
        # Overlap dates.
        with self.assertRaises(IntegrityError), transaction.atomic():
            reservation = HotelReservation(
                datespan=(datetimes[1].date(), datetimes[2].date()),
                start=datetimes[1],
                end=datetimes[2],
                room=room102,
            )
            msg = f"Constraint “{constraint.name}” is violated."
            with self.assertRaisesMessage(ValidationError, msg):
                constraint.validate(HotelReservation, reservation)
            reservation.save()
        # Valid range.
        other_valid_reservations = [
            # Other room.
            HotelReservation(
                datespan=(datetimes[1].date(), datetimes[2].date()),
                start=datetimes[1],
                end=datetimes[2],
                room=room101,
            ),
            # Cancelled reservation.
            HotelReservation(
                datespan=(datetimes[1].date(), datetimes[1].date()),
                start=datetimes[1],
                end=datetimes[2],
                room=room102,
                cancelled=True,
            ),
            # Other adjacent dates.
            HotelReservation(
                datespan=(datetimes[3].date(), datetimes[4].date()),
                start=datetimes[3],
                end=datetimes[4],
                room=room102,
            ),
        ]
        for reservation in other_valid_reservations:
            constraint.validate(HotelReservation, reservation)
        HotelReservation.objects.bulk_create(other_valid_reservations)
        # Excluded fields.
        constraint.validate(
            HotelReservation,
            HotelReservation(
                datespan=(datetimes[1].date(), datetimes[2].date()),
                start=datetimes[1],
                end=datetimes[2],
                room=room102,
            ),
            exclude={"room"},
        )
        constraint.validate(
            HotelReservation,
            HotelReservation(
                datespan=(datetimes[1].date(), datetimes[2].date()),
                start=datetimes[1],
                end=datetimes[2],
                room=room102,
            ),
            exclude={"datespan", "start", "end", "room"},
        )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_range_overlaps_custom_opclasses(self):
        class TsTzRange(Func):
            function = "TSTZRANGE"
            output_field = DateTimeRangeField()

        constraint = ExclusionConstraint(
            name="exclude_overlapping_reservations_custom",
            expressions=[
                (TsTzRange("start", "end", RangeBoundary()), RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
            opclasses=["range_ops", "gist_int4_ops"],
        )
        self._test_range_overlaps(constraint)

    def test_range_overlaps_custom(self):
        class TsTzRange(Func):
            function = "TSTZRANGE"
            output_field = DateTimeRangeField()

        constraint = ExclusionConstraint(
            name="exclude_overlapping_reservations_custom_opclass",
            expressions=[
                (
                    OpClass(TsTzRange("start", "end", RangeBoundary()), "range_ops"),
                    RangeOperators.OVERLAPS,
                ),
                (OpClass("room", "gist_int4_ops"), RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
        )
        self._test_range_overlaps(constraint)

    def test_range_overlaps(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping_reservations",
            expressions=[
                (F("datespan"), RangeOperators.OVERLAPS),
                ("room", RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
        )
        self._test_range_overlaps(constraint)

    def test_range_adjacent(self):
        constraint_name = "ints_adjacent"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        RangesModel.objects.create(ints=(20, 50))
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(ints=(10, 20))
        RangesModel.objects.create(ints=(10, 19))
        RangesModel.objects.create(ints=(51, 60))
        # Drop the constraint.
        with connection.schema_editor() as editor:
            editor.remove_constraint(RangesModel, constraint)
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )

    def test_validate_range_adjacent(self):
        constraint = ExclusionConstraint(
            name="ints_adjacent",
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            violation_error_message="Custom error message.",
        )
        range_obj = RangesModel.objects.create(ints=(20, 50))
        constraint.validate(RangesModel, range_obj)
        msg = "Custom error message."
        with self.assertRaisesMessage(ValidationError, msg):
            constraint.validate(RangesModel, RangesModel(ints=(10, 20)))
        constraint.validate(RangesModel, RangesModel(ints=(10, 19)))
        constraint.validate(RangesModel, RangesModel(ints=(51, 60)))
        constraint.validate(RangesModel, RangesModel(ints=(10, 20)), exclude={"ints"})

    def test_expressions_with_params(self):
        constraint_name = "scene_left_equal"
        self.assertNotIn(constraint_name, self.get_constraints(Scene._meta.db_table))
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[(Left("scene", 4), RangeOperators.EQUAL)],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(Scene, constraint)
        self.assertIn(constraint_name, self.get_constraints(Scene._meta.db_table))

    def test_expressions_with_key_transform(self):
        constraint_name = "exclude_overlapping_reservations_smoking"
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[
                (F("datespan"), RangeOperators.OVERLAPS),
                (KeyTextTransform("smoking", "requirements"), RangeOperators.EQUAL),
            ],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(HotelReservation, constraint)
        self.assertIn(
            constraint_name,
            self.get_constraints(HotelReservation._meta.db_table),
        )

    def test_index_transform(self):
        constraint_name = "first_index_equal"
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("field__0", RangeOperators.EQUAL)],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(IntegerArrayModel, constraint)
        self.assertIn(
            constraint_name,
            self.get_constraints(IntegerArrayModel._meta.db_table),
        )

    def test_range_adjacent_initially_deferred(self):
        constraint_name = "ints_adjacent_deferred"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            deferrable=Deferrable.DEFERRED,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        RangesModel.objects.create(ints=(20, 50))
        adjacent_range = RangesModel.objects.create(ints=(10, 20))
        # Constraint behavior can be changed with SET CONSTRAINTS.
        with self.assertRaises(IntegrityError):
            with transaction.atomic(), connection.cursor() as cursor:
                quoted_name = connection.ops.quote_name(constraint_name)
                cursor.execute("SET CONSTRAINTS %s IMMEDIATE" % quoted_name)
        # Remove adjacent range before the end of transaction.
        adjacent_range.delete()
        RangesModel.objects.create(ints=(10, 19))
        RangesModel.objects.create(ints=(51, 60))

    def test_range_adjacent_gist_include(self):
        constraint_name = "ints_adjacent_gist_include"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="gist",
            include=["decimals", "ints"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        RangesModel.objects.create(ints=(20, 50))
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(ints=(10, 20))
        RangesModel.objects.create(ints=(10, 19))
        RangesModel.objects.create(ints=(51, 60))

    @skipUnlessDBFeature("supports_covering_spgist_indexes")
    def test_range_adjacent_spgist_include(self):
        constraint_name = "ints_adjacent_spgist_include"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="spgist",
            include=["decimals", "ints"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        RangesModel.objects.create(ints=(20, 50))
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(ints=(10, 20))
        RangesModel.objects.create(ints=(10, 19))
        RangesModel.objects.create(ints=(51, 60))

    def test_range_adjacent_gist_include_condition(self):
        constraint_name = "ints_adjacent_gist_include_condition"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="gist",
            include=["decimals"],
            condition=Q(id__gte=100),
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    @skipUnlessDBFeature("supports_covering_spgist_indexes")
    def test_range_adjacent_spgist_include_condition(self):
        constraint_name = "ints_adjacent_spgist_include_condition"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="spgist",
            include=["decimals"],
            condition=Q(id__gte=100),
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    def test_range_adjacent_gist_include_deferrable(self):
        constraint_name = "ints_adjacent_gist_include_deferrable"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="gist",
            include=["decimals"],
            deferrable=Deferrable.DEFERRED,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    @skipUnlessDBFeature("supports_covering_spgist_indexes")
    def test_range_adjacent_spgist_include_deferrable(self):
        constraint_name = "ints_adjacent_spgist_include_deferrable"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="spgist",
            include=["decimals"],
            deferrable=Deferrable.DEFERRED,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    def test_spgist_include_not_supported(self):
        constraint_name = "ints_adjacent_spgist_include_not_supported"
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="spgist",
            include=["id"],
        )
        msg = (
            "Covering exclusion constraints using an SP-GiST index require "
            "PostgreSQL 14+."
        )
        with connection.schema_editor() as editor:
            with mock.patch(
                "django.db.backends.postgresql.features.DatabaseFeatures."
                "supports_covering_spgist_indexes",
                False,
            ):
                with self.assertRaisesMessage(NotSupportedError, msg):
                    editor.add_constraint(RangesModel, constraint)

    def test_range_adjacent_opclass(self):
        constraint_name = "ints_adjacent_opclass"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[
                (OpClass("ints", name="range_ops"), RangeOperators.ADJACENT_TO),
            ],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        constraints = self.get_constraints(RangesModel._meta.db_table)
        self.assertIn(constraint_name, constraints)
        with editor.connection.cursor() as cursor:
            cursor.execute(SchemaTests.get_opclass_query, [constraint_name])
            self.assertEqual(
                cursor.fetchall(),
                [("range_ops", constraint_name)],
            )
        RangesModel.objects.create(ints=(20, 50))
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(ints=(10, 20))
        RangesModel.objects.create(ints=(10, 19))
        RangesModel.objects.create(ints=(51, 60))
        # Drop the constraint.
        with connection.schema_editor() as editor:
            editor.remove_constraint(RangesModel, constraint)
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )

    def test_range_adjacent_opclass_condition(self):
        constraint_name = "ints_adjacent_opclass_condition"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[
                (OpClass("ints", name="range_ops"), RangeOperators.ADJACENT_TO),
            ],
            condition=Q(id__gte=100),
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    def test_range_adjacent_opclass_deferrable(self):
        constraint_name = "ints_adjacent_opclass_deferrable"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[
                (OpClass("ints", name="range_ops"), RangeOperators.ADJACENT_TO),
            ],
            deferrable=Deferrable.DEFERRED,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    def test_range_adjacent_gist_opclass_include(self):
        constraint_name = "ints_adjacent_gist_opclass_include"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[
                (OpClass("ints", name="range_ops"), RangeOperators.ADJACENT_TO),
            ],
            index_type="gist",
            include=["decimals"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    @skipUnlessDBFeature("supports_covering_spgist_indexes")
    def test_range_adjacent_spgist_opclass_include(self):
        constraint_name = "ints_adjacent_spgist_opclass_include"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[
                (OpClass("ints", name="range_ops"), RangeOperators.ADJACENT_TO),
            ],
            index_type="spgist",
            include=["decimals"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    def test_range_equal_cast(self):
        constraint_name = "exclusion_equal_room_cast"
        self.assertNotIn(constraint_name, self.get_constraints(Room._meta.db_table))
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[(Cast("number", IntegerField()), RangeOperators.EQUAL)],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(Room, constraint)
        self.assertIn(constraint_name, self.get_constraints(Room._meta.db_table))

    @isolate_apps("postgres_tests")
    def test_table_create(self):
        constraint_name = "exclusion_equal_number_tc"

        class ModelWithExclusionConstraint(Model):
            number = IntegerField()

            class Meta:
                app_label = "postgres_tests"
                constraints = [
                    ExclusionConstraint(
                        name=constraint_name,
                        expressions=[("number", RangeOperators.EQUAL)],
                    )
                ]

        with connection.schema_editor() as editor:
            editor.create_model(ModelWithExclusionConstraint)
        self.assertIn(
            constraint_name,
            self.get_constraints(ModelWithExclusionConstraint._meta.db_table),
        )


@modify_settings(INSTALLED_APPS={"append": "django.contrib.postgres"})
class ExclusionConstraintOpclassesDepracationTests(PostgreSQLTestCase):
    def get_constraints(self, table):
        """Get the constraints on the table using a new cursor."""
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_warning(self):
        msg = (
            "The opclasses argument is deprecated in favor of using "
            "django.contrib.postgres.indexes.OpClass in "
            "ExclusionConstraint.expressions."
        )
        with self.assertWarnsMessage(RemovedInDjango50Warning, msg):
            ExclusionConstraint(
                name="exclude_overlapping",
                expressions=[(F("datespan"), RangeOperators.ADJACENT_TO)],
                opclasses=["range_ops"],
            )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_repr(self):
        constraint = ExclusionConstraint(
            name="exclude_overlapping",
            expressions=[(F("datespan"), RangeOperators.ADJACENT_TO)],
            opclasses=["range_ops"],
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type='GIST' expressions=["
            "(F(datespan), '-|-')] name='exclude_overlapping' "
            "opclasses=['range_ops']>",
        )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_range_adjacent_opclasses(self):
        constraint_name = "ints_adjacent_opclasses"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            opclasses=["range_ops"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        constraints = self.get_constraints(RangesModel._meta.db_table)
        self.assertIn(constraint_name, constraints)
        with editor.connection.cursor() as cursor:
            cursor.execute(SchemaTests.get_opclass_query, [constraint.name])
            self.assertEqual(
                cursor.fetchall(),
                [("range_ops", constraint.name)],
            )
        RangesModel.objects.create(ints=(20, 50))
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(ints=(10, 20))
        RangesModel.objects.create(ints=(10, 19))
        RangesModel.objects.create(ints=(51, 60))
        # Drop the constraint.
        with connection.schema_editor() as editor:
            editor.remove_constraint(RangesModel, constraint)
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_range_adjacent_opclasses_condition(self):
        constraint_name = "ints_adjacent_opclasses_condition"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            opclasses=["range_ops"],
            condition=Q(id__gte=100),
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_range_adjacent_opclasses_deferrable(self):
        constraint_name = "ints_adjacent_opclasses_deferrable"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            opclasses=["range_ops"],
            deferrable=Deferrable.DEFERRED,
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_range_adjacent_gist_opclasses_include(self):
        constraint_name = "ints_adjacent_gist_opclasses_include"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="gist",
            opclasses=["range_ops"],
            include=["decimals"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))

    @ignore_warnings(category=RemovedInDjango50Warning)
    @skipUnlessDBFeature("supports_covering_spgist_indexes")
    def test_range_adjacent_spgist_opclasses_include(self):
        constraint_name = "ints_adjacent_spgist_opclasses_include"
        self.assertNotIn(
            constraint_name, self.get_constraints(RangesModel._meta.db_table)
        )
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[("ints", RangeOperators.ADJACENT_TO)],
            index_type="spgist",
            opclasses=["range_ops"],
            include=["decimals"],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
