from __future__ import unicode_literals

import pickle

from freedom.contrib.auth.models import User
from freedom.test import TestCase
from freedom.utils import six
from freedom.utils.functional import SimpleLazyObject


class TestUtilsSimpleLazyObjectFreedomTestCase(TestCase):

    def test_pickle_py2_regression(self):
        # See ticket #20212
        user = User.objects.create_user('johndoe', 'john@example.com', 'pass')
        x = SimpleLazyObject(lambda: user)

        # This would fail with "TypeError: can't pickle instancemethod objects",
        # only on Python 2.X.
        pickle.dumps(x)

        # Try the variant protocol levels.
        pickle.dumps(x, 0)
        pickle.dumps(x, 1)
        pickle.dumps(x, 2)

        if six.PY2:
            import cPickle

            # This would fail with "TypeError: expected string or Unicode object, NoneType found".
            cPickle.dumps(x)
