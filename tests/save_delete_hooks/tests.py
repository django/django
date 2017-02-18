from __future__ import unicode_literals

from django.test import TestCase
from django.utils import six

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
            six.text_type
        )

        p.delete()
        self.assertEqual(p.data, [
            "Before save",
            "After save",
            "Before deletion",
            "After deletion",
        ])
        self.assertQuerysetEqual(Person.objects.all(), [])
