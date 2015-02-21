import datetime
import os
import pickle
import subprocess
import sys
import warnings

from django.core.files.temp import NamedTemporaryFile
from django.db import DJANGO_VERSION_PICKLE_KEY, models
from django.test import TestCase
from django.utils.encoding import force_text
from django.utils.version import get_major_version, get_version

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
            pythonpath = [os.path.dirname(script.name)] + sys.path
            env = {
                # Needed to run test outside of tests directory
                str('PYTHONPATH'): os.pathsep.join(pythonpath),
                # Needed on Windows because http://bugs.python.org/issue8557
                str('PATH'): os.environ['PATH'],
                str('TMPDIR'): os.environ['TMPDIR'],
                str('LANG'): os.environ.get('LANG', ''),
            }
            if 'SYSTEMROOT' in os.environ:  # Windows http://bugs.python.org/issue20614
                env[str('SYSTEMROOT')] = os.environ['SYSTEMROOT']
            try:
                result = subprocess.check_output([sys.executable, script.name], env=env)
            except subprocess.CalledProcessError:
                self.fail("Unable to reload model pickled data")
        self.assertEqual(result.strip().decode(), "Some object")
