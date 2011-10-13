from __future__ import absolute_import

from django.test import TestCase

from .models import Person


class SaveDeleteHookTests(TestCase):
    def test_basic(self):
        p = Person(first_name="John", last_name="Smith")
        self.assertEqual(p.data, [])
        p.save()
        self.assertEqual(p.data, [
            "Before save",
            "After save",
        ])

        self.assertQuerysetEqual(
            Person.objects.all(), [
                "John Smith",
            ],
            unicode
        )

        p.delete()
        self.assertEqual(p.data, [
            "Before save",
            "After save",
            "Before deletion",
            "After deletion",
        ])
        self.assertQuerysetEqual(Person.objects.all(), [])
