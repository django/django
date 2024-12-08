import operator
import unittest
from collections import namedtuple
from contextlib import contextmanager

from django.db import connection, models
from django.db.utils import ProgrammingError
from django.test import TestCase
from django.test.utils import garbage_collect
from django.utils.version import PYPY

from ..models import Person

try:
    from django.db.backends.postgresql.psycopg_any import is_psycopg3
except ImportError:
    is_psycopg3 = False


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL tests")
class ServerSideCursorsPostgres(TestCase):
    cursor_fields = (
        "name, statement, is_holdable, is_binary, is_scrollable, creation_time"
    )
    PostgresCursor = namedtuple("PostgresCursor", cursor_fields)

    @classmethod
    def setUpTestData(cls):
        cls.p0 = Person.objects.create(first_name="a", last_name="a")
        cls.p1 = Person.objects.create(first_name="b", last_name="b")

    def inspect_cursors(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT {fields} FROM pg_cursors;".format(fields=self.cursor_fields)
            )
            cursors = cursor.fetchall()
        return [self.PostgresCursor._make(cursor) for cursor in cursors]

    @contextmanager
    def override_db_setting(self, **kwargs):
        for setting in kwargs:
            original_value = connection.settings_dict.get(setting)
            if setting in connection.settings_dict:
                self.addCleanup(
                    operator.setitem, connection.settings_dict, setting, original_value
                )
            else:
                self.addCleanup(operator.delitem, connection.settings_dict, setting)

            connection.settings_dict[setting] = kwargs[setting]
            yield

    def assertUsesCursor(self, queryset, num_expected=1):
        next(queryset)  # Open a server-side cursor
        cursors = self.inspect_cursors()
        self.assertEqual(len(cursors), num_expected)
        for cursor in cursors:
            self.assertIn("_django_curs_", cursor.name)
            self.assertFalse(cursor.is_scrollable)
            self.assertFalse(cursor.is_holdable)
            self.assertFalse(cursor.is_binary)

    def assertNotUsesCursor(self, queryset):
        self.assertUsesCursor(queryset, num_expected=0)

    def test_server_side_cursor(self):
        self.assertUsesCursor(Person.objects.iterator())

    def test_values(self):
        self.assertUsesCursor(Person.objects.values("first_name").iterator())

    def test_values_list(self):
        self.assertUsesCursor(Person.objects.values_list("first_name").iterator())

    def test_values_list_flat(self):
        self.assertUsesCursor(
            Person.objects.values_list("first_name", flat=True).iterator()
        )

    def test_values_list_fields_not_equal_to_names(self):
        expr = models.Count("id")
        self.assertUsesCursor(
            Person.objects.annotate(id__count=expr)
            .values_list(expr, "id__count")
            .iterator()
        )

    def test_server_side_cursor_many_cursors(self):
        persons = Person.objects.iterator()
        persons2 = Person.objects.iterator()
        next(persons)  # Open a server-side cursor
        self.assertUsesCursor(persons2, num_expected=2)

    def test_closed_server_side_cursor(self):
        persons = Person.objects.iterator()
        next(persons)  # Open a server-side cursor
        del persons
        garbage_collect()
        cursors = self.inspect_cursors()
        self.assertEqual(len(cursors), 0)

    @unittest.skipIf(
        PYPY,
        reason="Cursor not closed properly due to differences in garbage collection.",
    )
    def test_server_side_cursors_setting(self):
        with self.override_db_setting(DISABLE_SERVER_SIDE_CURSORS=False):
            persons = Person.objects.iterator()
            self.assertUsesCursor(persons)
            del persons  # Close server-side cursor

        # On PyPy, the cursor is left open here and attempting to force garbage
        # collection breaks the transaction wrapping the test.
        with self.override_db_setting(DISABLE_SERVER_SIDE_CURSORS=True):
            self.assertNotUsesCursor(Person.objects.iterator())

    @unittest.skipUnless(
        is_psycopg3, "The server_side_binding option is only effective on psycopg >= 3."
    )
    def test_server_side_binding(self):
        """
        The ORM still generates SQL that is not suitable for usage as prepared
        statements but psycopg >= 3 defaults to using server-side bindings for
        server-side cursors which requires some specialized logic when the
        `server_side_binding` setting is disabled (default).
        """

        def perform_query():
            # Generates SQL that is known to be problematic from a server-side
            # binding perspective as the parametrized ORDER BY clause doesn't
            # use the same binding parameter as the SELECT clause.
            qs = (
                Person.objects.order_by(
                    models.functions.Coalesce("first_name", models.Value(""))
                )
                .distinct()
                .iterator()
            )
            self.assertSequenceEqual(list(qs), [self.p0, self.p1])

        with self.override_db_setting(OPTIONS={}):
            perform_query()

        with self.override_db_setting(OPTIONS={"server_side_binding": False}):
            perform_query()

        with self.override_db_setting(OPTIONS={"server_side_binding": True}):
            # This assertion could start failing the moment the ORM generates
            # SQL suitable for usage as prepared statements (#20516) or if
            # psycopg >= 3 adapts psycopg.Connection(cursor_factory) machinery
            # to allow client-side bindings for named cursors. In the first
            # case this whole test could be removed, in the second one it would
            # most likely need to be adapted.
            with self.assertRaises(ProgrammingError):
                perform_query()
