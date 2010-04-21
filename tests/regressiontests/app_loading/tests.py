import copy
import os
import sys
import time
from unittest import TestCase

from django.conf import Settings
from django.db.models.loading import cache, load_app

__test__ = {"API_TESTS": """
Test the globbing of INSTALLED_APPS.

>>> old_sys_path = sys.path
>>> sys.path.append(os.path.dirname(os.path.abspath(__file__)))

>>> old_tz = os.environ.get("TZ")
>>> settings = Settings('test_settings')

>>> settings.INSTALLED_APPS
['parent.app', 'parent.app1', 'parent.app_2']

>>> sys.path = old_sys_path

# Undo a side-effect of installing a new settings object.
>>> if hasattr(time, "tzset") and old_tz:
...     os.environ["TZ"] = old_tz
...     time.tzset()

"""}

class EggLoadingTest(TestCase):

    def setUp(self):
        self.old_path = sys.path
        self.egg_dir = '%s/eggs' % os.path.dirname(__file__)

        # This test adds dummy applications to the app cache. These
        # need to be removed in order to prevent bad interactions
        # with the flush operation in other tests.
        self.old_app_models = copy.deepcopy(cache.app_models)
        self.old_app_store = copy.deepcopy(cache.app_store)

    def tearDown(self):
        sys.path = self.old_path
        cache.app_models = self.old_app_models
        cache.app_store = self.old_app_store

    def test_egg1(self):
        """Models module can be loaded from an app in an egg"""
        egg_name = '%s/modelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('app_with_models')
        self.failIf(models is None)

    def test_egg2(self):
        """Loading an app from an egg that has no models returns no models (and no error)"""
        egg_name = '%s/nomodelapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('app_no_models')
        self.failUnless(models is None)

    def test_egg3(self):
        """Models module can be loaded from an app located under an egg's top-level package"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('omelet.app_with_models')
        self.failIf(models is None)

    def test_egg4(self):
        """Loading an app with no models from under the top-level egg package generates no error"""
        egg_name = '%s/omelet.egg' % self.egg_dir
        sys.path.append(egg_name)
        models = load_app('omelet.app_no_models')
        self.failUnless(models is None)

    def test_egg5(self):
        """Loading an app from an egg that has an import error in its models module raises that error"""
        egg_name = '%s/brokenapp.egg' % self.egg_dir
        sys.path.append(egg_name)
        self.assertRaises(ImportError, load_app, 'broken_app')
        try:
            load_app('broken_app')
        except ImportError, e:
            # Make sure the message is indicating the actual
            # problem in the broken app.
            self.failUnless("modelz" in e.args[0])
