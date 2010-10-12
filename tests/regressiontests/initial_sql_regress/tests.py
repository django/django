from django.test import TestCase

from models import Simple


class InitialSQLTests(TestCase):
    def test_initial_sql(self):
        self.assertEqual(Simple.objects.count(), 7)
