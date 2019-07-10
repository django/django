import datetime

from django.db import connection, transaction
from django.db.models import F, Q
from django.db.models.constraints import CheckConstraint
from django.db.utils import IntegrityError

from . import PostgreSQLTestCase
from .models import RangesModel

try:
    from psycopg2.extras import NumericRange
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
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, RangesModel._meta.db_table)
        self.assertIn(constraint_name, constraints)
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
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, RangesModel._meta.db_table)
        self.assertIn(constraint_name, constraints)
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
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, RangesModel._meta.db_table)
        self.assertIn(constraint_name, constraints)
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
