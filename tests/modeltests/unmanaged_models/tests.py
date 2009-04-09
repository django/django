from django.test import TestCase
from django.db import connection
from models import Unmanaged1, Unmanaged2, Managed1

class ManyToManyUnmanagedTests(TestCase):
            
    def test_many_to_many_between_unmanaged(self):
        """
        The intermediary table between two unmanaged models should not be created.
        """
        table = Unmanaged2._meta.get_field('mm').m2m_db_table()
        tables = connection.introspection.table_names()
        self.assert_(table not in tables, "Table '%s' should not exist, but it does." % table)
        
    def test_many_to_many_between_unmanaged_and_managed(self):
        """
        An intermediary table between a managed and an unmanaged model should be created.
        """
        table = Managed1._meta.get_field('mm').m2m_db_table()
        tables = connection.introspection.table_names()
        self.assert_(table in tables, "Table '%s' does not exist." % table)
        