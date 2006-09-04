import unittest
from regressiontests.manager_db.models import Insect

class TestManagerDBAccess(unittest.TestCase):

    def test_db_property(self):
        m = Insect.objects
        db = Insect.objects.db
        assert db
        assert db.connection
        assert db.connection.cursor
        assert db.backend
        assert db.backend.quote_name
        assert db.get_creation_module

if __name__ == '__main__':
    unittest.main()
