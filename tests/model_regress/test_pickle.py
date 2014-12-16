import pickle
import warnings

from django.db import models, DJANGO_VERSION_PICKLE_KEY
from django.test import TestCase
from django.utils.encoding import force_text
from django.utils.version import get_major_version, get_version


class ModelPickleTestCase(TestCase):
    def test_missing_django_version_unpickling(self):
        """
        #21430 -- Verifies a warning is raised for models that are
        unpickled without a Django version
        """
        class MissingDjangoVersion(models.Model):
            title = models.CharField(max_length=10)

            def __reduce__(self):
                reduce_list = super(MissingDjangoVersion, self).__reduce__()
                data = reduce_list[-1]
                del data[DJANGO_VERSION_PICKLE_KEY]
                return reduce_list

        p = MissingDjangoVersion(title="FooBar")
        with warnings.catch_warnings(record=True) as recorded:
            pickle.loads(pickle.dumps(p))
            msg = force_text(recorded.pop().message)
            self.assertEqual(msg,
                "Pickled model instance's Django version is not specified.")

    def test_unsupported_unpickle(self):
        """
        #21430 -- Verifies a warning is raised for models that are
        unpickled with a different Django version than the current
        """
        class DifferentDjangoVersion(models.Model):
            title = models.CharField(max_length=10)

            def __reduce__(self):
                reduce_list = super(DifferentDjangoVersion, self).__reduce__()
                data = reduce_list[-1]
                data[DJANGO_VERSION_PICKLE_KEY] = str(float(get_major_version()) - 0.1)
                return reduce_list

        p = DifferentDjangoVersion(title="FooBar")
        with warnings.catch_warnings(record=True) as recorded:
            pickle.loads(pickle.dumps(p))
            msg = force_text(recorded.pop().message)
            self.assertEqual(msg,
                "Pickled model instance's Django version %s does not "
                "match the current version %s."
                % (str(float(get_major_version()) - 0.1), get_version()))
