from django.test import TestCase

from .models import Person


class GetAgainTests(TestCase):
    def test_get_again(self):
        p = Person.objects.create(name="foo")

        Person.objects.update(name="bar")

        p = p.get_again()
        self.assertEqual(p.name, "bar")
