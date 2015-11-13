import datetime
import os
import pickle
import subprocess
import sys

from django.core.files.temp import NamedTemporaryFile
from django.db import DJANGO_VERSION_PICKLE_KEY, models
from django.test import TestCase, mock
from django.utils._os import npath, upath
from django.utils.version import get_version

from .models import Article


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
        msg = "Pickled model instance's Django version is not specified."
        with self.assertRaisesMessage(RuntimeWarning, msg):
            pickle.loads(pickle.dumps(p))

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
                data[DJANGO_VERSION_PICKLE_KEY] = '1.0'
                return reduce_list

        p = DifferentDjangoVersion(title="FooBar")
        msg = "Pickled model instance's Django version 1.0 does not match the current version %s." % get_version()
        with self.assertRaisesMessage(RuntimeWarning, msg):
            pickle.loads(pickle.dumps(p))

    def test_unpickling_when_appregistrynotready(self):
        """
        #24007 -- Verifies that a pickled model can be unpickled without having
        to manually setup the apps registry beforehand.
        """
        script_template = """#!/usr/bin/env python
import pickle

from django.conf import settings

data = %r

settings.configure(DEBUG=False, INSTALLED_APPS=('model_regress',), SECRET_KEY = "blah")
article = pickle.loads(data)
print(article.headline)"""
        a = Article.objects.create(
            headline="Some object",
            pub_date=datetime.datetime.now(),
            article_text="This is an article",
        )

        with NamedTemporaryFile(mode='w+', suffix=".py") as script:
            script.write(script_template % pickle.dumps(a))
            script.flush()
            # A path to model_regress must be set in PYTHONPATH
            model_regress_dir = os.path.dirname(upath(__file__))
            model_regress_path = os.path.abspath(model_regress_dir)
            tests_path = os.path.split(model_regress_path)[0]
            pythonpath = os.environ.get('PYTHONPATH', '')
            pythonpath = npath(os.pathsep.join([tests_path, pythonpath]))

            with mock.patch.dict('os.environ', {'PYTHONPATH': pythonpath}):
                try:
                    result = subprocess.check_output([sys.executable, script.name])
                except subprocess.CalledProcessError:
                    self.fail("Unable to reload model pickled data")
        self.assertEqual(result.strip().decode(), "Some object")
