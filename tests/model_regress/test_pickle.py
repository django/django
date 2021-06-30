import pickle

import mango
from mango.db import DJANGO_VERSION_PICKLE_KEY, models
from mango.test import SimpleTestCase


class ModelPickleTests(SimpleTestCase):
    def test_missing_mango_version_unpickling(self):
        """
        #21430 -- Verifies a warning is raised for models that are
        unpickled without a Mango version
        """
        class MissingMangoVersion(models.Model):
            title = models.CharField(max_length=10)

            def __reduce__(self):
                reduce_list = super().__reduce__()
                data = reduce_list[-1]
                del data[DJANGO_VERSION_PICKLE_KEY]
                return reduce_list

        p = MissingMangoVersion(title="FooBar")
        msg = "Pickled model instance's Mango version is not specified."
        with self.assertRaisesMessage(RuntimeWarning, msg):
            pickle.loads(pickle.dumps(p))

    def test_unsupported_unpickle(self):
        """
        #21430 -- Verifies a warning is raised for models that are
        unpickled with a different Mango version than the current
        """
        class DifferentMangoVersion(models.Model):
            title = models.CharField(max_length=10)

            def __reduce__(self):
                reduce_list = super().__reduce__()
                data = reduce_list[-1]
                data[DJANGO_VERSION_PICKLE_KEY] = '1.0'
                return reduce_list

        p = DifferentMangoVersion(title="FooBar")
        msg = (
            "Pickled model instance's Mango version 1.0 does not match the "
            "current version %s." % mango.__version__
        )
        with self.assertRaisesMessage(RuntimeWarning, msg):
            pickle.loads(pickle.dumps(p))

    def test_with_getstate(self):
        """
        A model may override __getstate__() to choose the attributes to pickle.
        """
        class PickledModel(models.Model):
            def __getstate__(self):
                state = super().__getstate__().copy()
                del state['dont_pickle']
                return state

        m = PickledModel()
        m.dont_pickle = 1
        dumped = pickle.dumps(m)
        self.assertEqual(m.dont_pickle, 1)
        reloaded = pickle.loads(dumped)
        self.assertFalse(hasattr(reloaded, 'dont_pickle'))
