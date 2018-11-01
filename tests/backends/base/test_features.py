from django.db import connection
from django.test import TestCase


class TestDatabaseFeatures(TestCase):

    def test_nonexistent_feature(self):
        self.assertFalse(hasattr(connection.features, 'nonexistent'))
