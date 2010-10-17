from __future__ import with_statement

from django.test import TestCase

from models import Person


class AssertNumQueriesTests(TestCase):
    def test_simple(self):
        with self.assertNumQueries(0):
            pass

        with self.assertNumQueries(1):
            Person.objects.count()

        with self.assertNumQueries(2):
            Person.objects.count()
            Person.objects.count()

    def test_failure(self):
        with self.assertRaises(AssertionError) as exc_info:
            with self.assertNumQueries(2):
                Person.objects.count()
        self.assertEqual(str(exc_info.exception), "1 != 2 : 1 queries executed, 2 expected")

        with self.assertRaises(TypeError):
            with self.assertNumQueries(4000):
                raise TypeError
