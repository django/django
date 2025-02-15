import pickle

from thibaud.contrib.auth.models import User
from thibaud.test import TestCase
from thibaud.utils.functional import SimpleLazyObject


class TestUtilsSimpleLazyObjectThibaudTestCase(TestCase):
    def test_pickle(self):
        user = User.objects.create_user("johndoe", "john@example.com", "pass")
        x = SimpleLazyObject(lambda: user)
        pickle.dumps(x)
        # Try the variant protocol levels.
        pickle.dumps(x, 0)
        pickle.dumps(x, 1)
        pickle.dumps(x, 2)
