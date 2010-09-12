from datetime import date

from django.db import IntegrityError
from django.test import TestCase

from models import Person, ManualPrimaryKeyTest


class GetOrCreateTests(TestCase):
    def test_get_or_create(self):
        p = Person.objects.create(
            first_name='John', last_name='Lennon', birthday=date(1940, 10, 9)
        )

        p, created = Person.objects.get_or_create(
            first_name="John", last_name="Lennon", defaults={
                "birthday": date(1940, 10, 9)
            }
        )
        self.assertFalse(created)
        self.assertEqual(Person.objects.count(), 1)

        p, created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        self.assertTrue(created)
        self.assertEqual(Person.objects.count(), 2)

        # If we execute the exact same statement, it won't create a Person.
        p, created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        self.assertFalse(created)
        self.assertEqual(Person.objects.count(), 2)

        # If you don't specify a value or default value for all required
        # fields, you will get an error.
        self.assertRaises(IntegrityError,
            Person.objects.get_or_create, first_name="Tom", last_name="Smith"
        )

        # If you specify an existing primary key, but different other fields,
        # then you will get an error and data will not be updated.
        m = ManualPrimaryKeyTest.objects.create(id=1, data="Original")
        self.assertRaises(IntegrityError,
            ManualPrimaryKeyTest.objects.get_or_create, id=1, data="Different"
        )
        self.assertEqual(ManualPrimaryKeyTest.objects.get(id=1).data, "Original")
