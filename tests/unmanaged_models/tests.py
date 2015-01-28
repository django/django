from __future__ import unicode_literals

from django.db import connection
from django.test import TestCase

from .models import A01, A02, B01, B02, C01, C02, Managed1, Unmanaged2


class SimpleTests(TestCase):

    def test_simple(self):
        """
        The main test here is that the all the models can be created without
        any database errors. We can also do some more simple insertion and
        lookup tests whilst we're here to show that the second of models do
        refer to the tables from the first set.
        """
        # Insert some data into one set of models.
        a = A01.objects.create(f_a="foo", f_b=42)
        B01.objects.create(fk_a=a, f_a="fred", f_b=1729)
        c = C01.objects.create(f_a="barney", f_b=1)
        c.mm_a = [a]

        # ... and pull it out via the other set.
        a2 = A02.objects.all()[0]
        self.assertIsInstance(a2, A02)
        self.assertEqual(a2.f_a, "foo")

        b2 = B02.objects.all()[0]
        self.assertIsInstance(b2, B02)
        self.assertEqual(b2.f_a, "fred")

        self.assertIsInstance(b2.fk_a, A02)
        self.assertEqual(b2.fk_a.f_a, "foo")

        self.assertEqual(list(C02.objects.filter(f_a=None)), [])

        resp = list(C02.objects.filter(mm_a=a.id))
        self.assertEqual(len(resp), 1)

        self.assertIsInstance(resp[0], C02)
        self.assertEqual(resp[0].f_a, 'barney')


class ManyToManyUnmanagedTests(TestCase):

    def test_many_to_many_between_unmanaged(self):
        """
        The intermediary table between two unmanaged models should not be created.
        """
        table = Unmanaged2._meta.get_field('mm').m2m_db_table()
        tables = connection.introspection.table_names()
        self.assertNotIn(table, tables, "Table '%s' should not exist, but it does." % table)

    def test_many_to_many_between_unmanaged_and_managed(self):
        """
        An intermediary table between a managed and an unmanaged model should be created.
        """
        table = Managed1._meta.get_field('mm').m2m_db_table()
        tables = connection.introspection.table_names()
        self.assertIn(table, tables, "Table '%s' does not exist." % table)
