import unittest
from collections import namedtuple

from django.db import connection
from django.test import TestCase

from .models import Person


@unittest.skipUnless(connection.vendor == 'postgresql', "Test only for PostgreSQL")
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
