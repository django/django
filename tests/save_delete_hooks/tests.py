from django.test import TestCase

from .models import Person


class SaveDeleteHookTests(TestCase):
    def test_basic(self):
        p = Person(first_name="John", last_name="Smith")
        self.assertEqual(p.data, [])
        p.save()
        self.assertEqual(
            p.data,
            [
                "Before save",
                "After save",
            ],
        )

        self.assertQuerySetEqual(
            Person.objects.all(),
            [
                "John Smith",
            ],
            str,
        )

        p.delete()
        self.assertEqual(
            p.data,
            [
                "Before save",
                "After save",
                "Before deletion",
                "After deletion",
            ],
        )
        self.assertQuerySetEqual(Person.objects.all(), [])
