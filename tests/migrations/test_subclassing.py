from django.core.management import call_command
from django.db import connection
from django.test import override_settings

from .test_base import MigrationTestBase


class TestDisconnectSubclass(MigrationTestBase):
    @override_settings(MIGRATION_MODULES={'migrations': 'migrations.subclass_migrations'})
    def test_migrate(self):
        expected_data = ((1, 10), (2, 20), (3, 30), (4, 40))

        # Test base state
        call_command('migrate', 'migrations', '0002', verbosity=0)
        self.assertFKExists('migrations_child', ['parent_ptr_id'], ('migrations_parent', 'id'))

        with connection.cursor() as cursor:
            cursor.execute('select parent_ptr_id, age from migrations_child')
            data = cursor.fetchall()
        self.assertSequenceEqual(data, expected_data)

        # Test migrate forwards
        call_command('migrate', 'migrations', '0003', verbosity=0)
        self.assertFKNotExists('migrations_child', ['parent_ptr_id'], ('migrations_parent', 'id'))

        with connection.cursor() as cursor:
            cursor.execute('select id, age from migrations_child')
            data = cursor.fetchall()
        self.assertSequenceEqual(data, expected_data)

        # Test migrate backwards
        call_command('migrate', 'migrations', '0002', verbosity=0)
        self.assertFKExists('migrations_child', ['parent_ptr_id'], ('migrations_parent', 'id'))

        with connection.cursor() as cursor:
            cursor.execute('select parent_ptr_id, age from migrations_child')
            data = cursor.fetchall()
        self.assertSequenceEqual(data, expected_data)
