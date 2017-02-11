import operator
import unittest
from collections import namedtuple
from contextlib import contextmanager

from django.db import connection
from django.test import TestCase

from ..models import Person


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL tests')
class ServerSideCursorsPostgres(TestCase):
    cursor_fields = 'name, statement, is_holdable, is_binary, is_scrollable, creation_time'
    PostgresCursor = namedtuple('PostgresCursor', cursor_fields)

    @classmethod
    def setUpTestData(cls):
        Person.objects.create(first_name='a', last_name='a')
        Person.objects.create(first_name='b', last_name='b')

    def inspect_cursors(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT {fields} FROM pg_cursors;'.format(fields=self.cursor_fields))
            cursors = cursor.fetchall()
        return [self.PostgresCursor._make(cursor) for cursor in cursors]

    @contextmanager
    def override_db_setting(self, **kwargs):
        for setting, value in kwargs.items():
            original_value = connection.settings_dict.get(setting)
            if setting in connection.settings_dict:
                self.addCleanup(operator.setitem, connection.settings_dict, setting, original_value)
            else:
                self.addCleanup(operator.delitem, connection.settings_dict, setting)

            connection.settings_dict[setting] = kwargs[setting]
            yield

    def test_server_side_cursor(self):
        persons = Person.objects.iterator()
        next(persons)  # Open a server-side cursor
        cursors = self.inspect_cursors()
        self.assertEqual(len(cursors), 1)
        self.assertIn('_django_curs_', cursors[0].name)
        self.assertFalse(cursors[0].is_scrollable)
        self.assertFalse(cursors[0].is_holdable)
        self.assertFalse(cursors[0].is_binary)

    def test_server_side_cursor_many_cursors(self):
        persons = Person.objects.iterator()
        persons2 = Person.objects.iterator()
        next(persons)  # Open a server-side cursor
        next(persons2)  # Open a second server-side cursor
        cursors = self.inspect_cursors()
        self.assertEqual(len(cursors), 2)
        for cursor in cursors:
            self.assertIn('_django_curs_', cursor.name)
            self.assertFalse(cursor.is_scrollable)
            self.assertFalse(cursor.is_holdable)
            self.assertFalse(cursor.is_binary)

    def test_closed_server_side_cursor(self):
        persons = Person.objects.iterator()
        next(persons)  # Open a server-side cursor
        del persons
        cursors = self.inspect_cursors()
        self.assertEqual(len(cursors), 0)

    def test_server_side_cursors_setting(self):
        with self.override_db_setting(DISABLE_SERVER_SIDE_CURSORS=False):
            persons = Person.objects.iterator()
            next(persons)  # Open a server-side cursor
            cursors = self.inspect_cursors()
            self.assertEqual(len(cursors), 1)
            del persons  # Close server-side cursor

        with self.override_db_setting(DISABLE_SERVER_SIDE_CURSORS=True):
            persons = Person.objects.iterator()
            next(persons)  # Should not open a server-side cursor
            cursors = self.inspect_cursors()
            self.assertEqual(len(cursors), 0)
