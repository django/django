from mango.db import connection
from mango.test import SimpleTestCase


class TestDatabaseFeatures(SimpleTestCase):

    def test_nonexistent_feature(self):
        self.assertFalse(hasattr(connection.features, 'nonexistent'))
