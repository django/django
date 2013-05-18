from __future__ import absolute_import

from datetime import date

from django.db.utils import IntegrityError
from django.test import TestCase

from .models import Person


class UpdateOrCreateTests(TestCase):

    def test_update(self):
        Person.objects.create(
            first_name='John', last_name='Lennon', birthday=date(1940, 10, 9)
        )
        p, created = Person.objects.update_or_create(
            first_name='John', last_name='Lennon', defaults={
                'birthday': date(1940, 10, 10)
            }
        )
        self.assertFalse(created)
        self.assertEqual(p.first_name, 'John')
        self.assertEqual(p.last_name, 'Lennon')
        self.assertEqual(p.birthday, date(1940, 10, 10))

    def test_create(self):
        p, created = Person.objects.update_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        self.assertTrue(created)
        self.assertEqual(p.first_name, 'George')
        self.assertEqual(p.last_name, 'Harrison')
        self.assertEqual(p.birthday, date(1943, 2, 25))

    def test_create_twice(self):
        Person.objects.update_or_create(
            first_name='Django', last_name='Pony', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        # If we execute the exact same statement, it won't create a Person.
        p, created = Person.objects.update_or_create(
            first_name='Django', last_name='Pony', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        self.assertFalse(created)

    def test_integrity(self):
        # If you don't specify a value or default value for all required
        # fields, you will get an error.
        self.assertRaises(IntegrityError, Person.objects.update_or_create, first_name='Tom', last_name='Smith')
