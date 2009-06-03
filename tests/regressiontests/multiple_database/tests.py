from django.conf import settings
from django.db import connections
from django.test import TestCase

class DatabaseSettingTestCase(TestCase):
    def setUp(self):
        settings.DATABASES['__test_db'] = {
            'DATABASE_ENGINE': 'sqlite3',
            'DATABASE_NAME': ':memory:',
        }

    def tearDown(self):
        del settings.DATABASES['__test_db']

    def test_db_connection(self):
        connections['default'].cursor()
        connections['__test_db'].cursor()
