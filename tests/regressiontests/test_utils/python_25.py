from __future__ import with_statement

from django.test import TestCase

from models import Person


class AssertNumQueriesTests(TestCase):
    def test_simple(self):
        with self.assertNumQueries(0):
            pass

        with self.assertNumQueries(1):
            # Guy who wrote Linux
            Person.objects.create(name="Linus Torvalds")

        with self.assertNumQueries(2):
            # Guy who owns the bagel place I like
            Person.objects.create(name="Uncle Ricky")
            self.assertEqual(Person.objects.count(), 2)

    def test_failure(self):
        with self.assertRaises(AssertionError) as exc_info:
            with self.assertNumQueries(2):
                Person.objects.count()
        self.assertEqual(str(exc_info.exception), "1 != 2 : 1 queries executed, 2 expected")

        with self.assertRaises(TypeError):
            with self.assertNumQueries(4000):
                raise TypeError
