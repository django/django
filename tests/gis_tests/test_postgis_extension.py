import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class TestsPostGISCreateExtension(TestCase):

    def setUp(self):
        """
        Make extension is not available initially
        """
        new_connection = connection.copy()
        try:
            with new_connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT installed_version FROM
                    pg_available_extensions WHERE name = 'postgis';
                    """
                )
                if cursor.fetchone()[0] is not None:
                    cursor.execute("""DROP EXTENSION postgis CASCADE;""")
        finally:
            new_connection.close()

    def test_extension_is_created(self):
        """
        Create PostGIS extension
        if it does not exists.
        """
        new_connection = connection.copy()
        try:
            with new_connection.cursor() as cursor:
                cursor.execute(
                    """SELECT installed_version
                    FROM pg_available_extensions
                    WHERE name ='postgis';"""
                )
                self.assertIsNone(cursor.fetchone()[0])
                new_connection.prepare_database()
                cursor.execute(
                    """SELECT installed_version
                    FROM pg_available_extensions
                    WHERE name ='postgis';"""
                )
                self.assertTrue(cursor.fetchone()[0])
                new_connection.close()
        finally:
            new_connection.close()

    def test_extension_is_not_created(self):
        """
        Dont create PostGIS extension
        if it exists.
        """
        new_connection = connection.copy()
        try:
            with new_connection.cursor() as cursor:
                cursor.execute(
                    """SELECT installed_version
                    FROM pg_available_extensions
                    WHERE name ='postgis';"""
                )
                new_connection.prepare_database()
                cursor.execute(
                    """SELECT installed_version
                    FROM pg_available_extensions
                    WHERE name ='postgis';"""
                )
                self.assertTrue(cursor.fetchone()[0])
        finally:
            new_connection.prepare_database()
            new_connection.close()
