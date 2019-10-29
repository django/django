import datetime
from unittest import mock

from django.db import connection, transaction
from django.db.models import F, Func, Q
from django.db.models.constraints import CheckConstraint
from django.db.utils import IntegrityError
from django.utils import timezone

from . import PostgreSQLTestCase
from .models import HotelReservation, RangesModel, Room

try:
    from django.contrib.postgres.constraints import ExclusionConstraint
    from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators

    from psycopg2.extras import DateRange, NumericRange
except ImportError:
    pass


class SchemaTests(PostgreSQLTestCase):
    def get_constraints(self, table):
        """Get the constraints on the table using a new cursor."""
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_check_constraint_range_value(self):
        constraint_name = 'ints_between'
        self.assertNotIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
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

    def test_check_constraint_daterange_contains(self):
        constraint_name = 'dates_contains'
        self.assertNotIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        constraint = CheckConstraint(
            check=Q(dates__contains=F('dates_inner')),
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
        constraint_name = 'timestamps_contains'
        self.assertNotIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        constraint = CheckConstraint(
            check=Q(timestamps__contains=F('timestamps_inner')),
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


class ExclusionConstraintTests(PostgreSQLTestCase):
    def get_constraints(self, table):
        """Get the constraints on the table using a new cursor."""
        with connection.cursor() as cursor:
            return connection.introspection.get_constraints(cursor, table)

    def test_invalid_condition(self):
        msg = 'ExclusionConstraint.condition must be a Q instance.'
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                index_type='GIST',
                name='exclude_invalid_condition',
                expressions=[(F('datespan'), RangeOperators.OVERLAPS)],
                condition=F('invalid'),
            )

    def test_invalid_index_type(self):
        msg = 'Exclusion constraints only support GiST or SP-GiST indexes.'
        with self.assertRaisesMessage(ValueError, msg):
            ExclusionConstraint(
                index_type='gin',
                name='exclude_invalid_index_type',
                expressions=[(F('datespan'), RangeOperators.OVERLAPS)],
            )

    def test_invalid_expressions(self):
        msg = 'The expressions must be a list of 2-tuples.'
        for expressions in (['foo'], [('foo')], [('foo_1', 'foo_2', 'foo_3')]):
            with self.subTest(expressions), self.assertRaisesMessage(ValueError, msg):
                ExclusionConstraint(
                    index_type='GIST',
                    name='exclude_invalid_expressions',
                    expressions=expressions,
                )

    def test_empty_expressions(self):
        msg = 'At least one expression is required to define an exclusion constraint.'
        for empty_expressions in (None, []):
            with self.subTest(empty_expressions), self.assertRaisesMessage(ValueError, msg):
                ExclusionConstraint(
                    index_type='GIST',
                    name='exclude_empty_expressions',
                    expressions=empty_expressions,
                )

    def test_repr(self):
        constraint = ExclusionConstraint(
            name='exclude_overlapping',
            expressions=[
                (F('datespan'), RangeOperators.OVERLAPS),
                (F('room'), RangeOperators.EQUAL),
            ],
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type=GIST, expressions=["
            "(F(datespan), '&&'), (F(room), '=')]>",
        )
        constraint = ExclusionConstraint(
            name='exclude_overlapping',
            expressions=[(F('datespan'), RangeOperators.ADJACENT_TO)],
            condition=Q(cancelled=False),
            index_type='SPGiST',
        )
        self.assertEqual(
            repr(constraint),
            "<ExclusionConstraint: index_type=SPGiST, expressions=["
            "(F(datespan), '-|-')], condition=(AND: ('cancelled', False))>",
        )

    def test_eq(self):
        constraint_1 = ExclusionConstraint(
            name='exclude_overlapping',
            expressions=[
                (F('datespan'), RangeOperators.OVERLAPS),
                (F('room'), RangeOperators.EQUAL),
            ],
            condition=Q(cancelled=False),
        )
        constraint_2 = ExclusionConstraint(
            name='exclude_overlapping',
            expressions=[
                ('datespan', RangeOperators.OVERLAPS),
                ('room', RangeOperators.EQUAL),
            ],
        )
        constraint_3 = ExclusionConstraint(
            name='exclude_overlapping',
            expressions=[('datespan', RangeOperators.OVERLAPS)],
            condition=Q(cancelled=False),
        )
        self.assertEqual(constraint_1, constraint_1)
        self.assertEqual(constraint_1, mock.ANY)
        self.assertNotEqual(constraint_1, constraint_2)
        self.assertNotEqual(constraint_1, constraint_3)
        self.assertNotEqual(constraint_2, constraint_3)
        self.assertNotEqual(constraint_1, object())

    def test_deconstruct(self):
        constraint = ExclusionConstraint(
            name='exclude_overlapping',
            expressions=[('datespan', RangeOperators.OVERLAPS), ('room', RangeOperators.EQUAL)],
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.constraints.ExclusionConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {
            'name': 'exclude_overlapping',
            'expressions': [('datespan', RangeOperators.OVERLAPS), ('room', RangeOperators.EQUAL)],
        })

    def test_deconstruct_index_type(self):
        constraint = ExclusionConstraint(
            name='exclude_overlapping',
            index_type='SPGIST',
            expressions=[('datespan', RangeOperators.OVERLAPS), ('room', RangeOperators.EQUAL)],
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.constraints.ExclusionConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {
            'name': 'exclude_overlapping',
            'index_type': 'SPGIST',
            'expressions': [('datespan', RangeOperators.OVERLAPS), ('room', RangeOperators.EQUAL)],
        })

    def test_deconstruct_condition(self):
        constraint = ExclusionConstraint(
            name='exclude_overlapping',
            expressions=[('datespan', RangeOperators.OVERLAPS), ('room', RangeOperators.EQUAL)],
            condition=Q(cancelled=False),
        )
        path, args, kwargs = constraint.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.constraints.ExclusionConstraint')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {
            'name': 'exclude_overlapping',
            'expressions': [('datespan', RangeOperators.OVERLAPS), ('room', RangeOperators.EQUAL)],
            'condition': Q(cancelled=False),
        })

    def _test_range_overlaps(self, constraint):
        # Create exclusion constraint.
        self.assertNotIn(constraint.name, self.get_constraints(HotelReservation._meta.db_table))
        with connection.schema_editor() as editor:
            editor.add_constraint(HotelReservation, constraint)
        self.assertIn(constraint.name, self.get_constraints(HotelReservation._meta.db_table))
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
        HotelReservation.objects.create(
            datespan=DateRange(datetimes[0].date(), datetimes[1].date()),
            start=datetimes[0],
            end=datetimes[1],
            room=room102,
        )
        HotelReservation.objects.create(
            datespan=DateRange(datetimes[1].date(), datetimes[3].date()),
            start=datetimes[1],
            end=datetimes[3],
            room=room102,
        )
        # Overlap dates.
        with self.assertRaises(IntegrityError), transaction.atomic():
            reservation = HotelReservation(
                datespan=(datetimes[1].date(), datetimes[2].date()),
                start=datetimes[1],
                end=datetimes[2],
                room=room102,
            )
            reservation.save()
        # Valid range.
        HotelReservation.objects.bulk_create([
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
        ])

    def test_range_overlaps_custom(self):
        class TsTzRange(Func):
            function = 'TSTZRANGE'
            output_field = DateTimeRangeField()

        constraint = ExclusionConstraint(
            name='exclude_overlapping_reservations_custom',
            expressions=[
                (TsTzRange('start', 'end', RangeBoundary()), RangeOperators.OVERLAPS),
                ('room', RangeOperators.EQUAL)
            ],
            condition=Q(cancelled=False),
        )
        self._test_range_overlaps(constraint)

    def test_range_overlaps(self):
        constraint = ExclusionConstraint(
            name='exclude_overlapping_reservations',
            expressions=[
                (F('datespan'), RangeOperators.OVERLAPS),
                ('room', RangeOperators.EQUAL)
            ],
            condition=Q(cancelled=False),
        )
        self._test_range_overlaps(constraint)

    def test_range_adjacent(self):
        constraint_name = 'ints_adjacent'
        self.assertNotIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        constraint = ExclusionConstraint(
            name=constraint_name,
            expressions=[('ints', RangeOperators.ADJACENT_TO)],
        )
        with connection.schema_editor() as editor:
            editor.add_constraint(RangesModel, constraint)
        self.assertIn(constraint_name, self.get_constraints(RangesModel._meta.db_table))
        RangesModel.objects.create(ints=(20, 50))
        with self.assertRaises(IntegrityError), transaction.atomic():
            RangesModel.objects.create(ints=(10, 20))
        RangesModel.objects.create(ints=(10, 19))
        RangesModel.objects.create(ints=(51, 60))
