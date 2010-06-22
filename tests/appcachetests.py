import copy
import sys
import unittest
import threading
from django.conf import settings
from django.utils.datastructures import SortedDict
from django.core.exceptions import ImproperlyConfigured

# remove when tests are integrated into the django testsuite
settings.configure()

from django.db.models.loading import cache

class AppCacheTestCase(unittest.TestCase):
    """
    TestCase that resets the AppCache after each test.
    """
    def setUp(self):
        self.old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = ()

    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps

        # The appcache imports models modules. We need to delete the
        # imported module from sys.modules after the test has run. 
        # If the module is imported again, the ModelBase.__new__ can 
        # register the models with the appcache anew.
        # Some models modules import other models modules (for example 
        # django.contrib.auth relies on django.contrib.contenttypes). 
        # To detect which model modules have been imported, we go through
        # all loaded model classes and remove their respective module 
        # from sys.modules
        for app in cache.app_models.itervalues():
            for name in app.itervalues():
                module = name.__module__
                if module in sys.modules:
                    del sys.modules[module]

        # we cannot copy() the whole cache.__dict__ in the setUp function
        # because thread.RLock is un(deep)copyable
        cache.app_store = SortedDict()
        cache.app_models = SortedDict()
        cache.app_errors = {}
        cache.loaded = False
        cache.handled = {}
        cache.postponed = []
        cache.nesting_level = 0
        cache.write_lock = threading.RLock()
        cache._get_models_cache = {}

class AppCacheReadyTests(AppCacheTestCase):
    """
    Tests for the app_cache_ready function that indicates if the cache
    is fully populated.
    """
    def test_not_initialized(self):
        """Should return False if the AppCache hasn't been initialized"""
        self.assertFalse(cache.app_cache_ready())

    def test_load_app(self):
        """Should return False after executing the load_app function"""
        cache.load_app('django.contrib.comments')
        self.assertFalse(cache.app_cache_ready())
        cache.load_app('django.contrib.comments', can_postpone=True)
        self.assertFalse(cache.app_cache_ready())

class GetAppsTests(AppCacheTestCase):
    """Tests for the get_apps function"""
    def test_get_apps(self):
        """Test that the correct models modules are returned"""
        settings.INSTALLED_APPS = ('django.contrib.auth',
                                   'django.contrib.flatpages',)
        apps = cache.get_apps()
        self.assertEqual(len(apps), 2)
        self.assertTrue(apps[0], 'django.contrib.auth.models')
        self.assertTrue(apps[1], 'django.contrib.flatpages.models')
        self.assertTrue(cache.app_cache_ready())

    def test_empty_models(self):
        """Test that modules that don't contain models are not returned"""
        settings.INSTALLED_APPS = ('django.contrib.csrf',)
        self.assertEqual(cache.get_apps(), [])
        self.assertTrue(cache.app_cache_ready())

class GetAppTests(AppCacheTestCase):
    """Tests for the get_app function"""
    def test_get_app(self):
        """Test that the correct module is returned"""
        settings.INSTALLED_APPS = ('django.contrib.auth',)
        module = cache.get_app('auth')
        self.assertTrue(module, 'django.contrib.auth.models')
        self.assertTrue(cache.app_cache_ready())

    def test_not_found_exception(self):
        """
        Test that an ImproperlyConfigured exception is raised if an app
        could not be found
        """
        self.assertRaises(ImproperlyConfigured, cache.get_app,
                          'django.contrib.auth')
        self.assertTrue(cache.app_cache_ready())

    def test_emptyOK(self):
        """
        Test that None is returned if emptyOK is True and the module
        has no models
        """
        settings.INSTALLED_APPS = ('django.contrib.csrf',)
        module = cache.get_app('csrf', emptyOK=True)
        self.failUnless(module is None)
        self.assertTrue(cache.app_cache_ready())

    def test_load_app_modules(self):
        """
        Test that only apps that are listed in the INSTALLED_APPS setting 
        are searched (unlike the get_apps function, which also searches
        apps that are loaded via load_app)
        """
        cache.load_app('django.contrib.sites')
        self.assertRaises(ImproperlyConfigured, cache.get_app, 'sites')
        self.assertTrue(cache.app_cache_ready())

class GetAppErrorsTests(AppCacheTestCase):
    """Tests for the get_app_errors function"""
    def test_get_app_errors(self):
        """Test that the function returns an empty dict"""
        self.assertEqual(cache.get_app_errors(), {})
        self.assertTrue(cache.app_cache_ready())

class GetModelsTests(AppCacheTestCase):
    """Tests for the get_models function"""
    def test_get_models(self):
        """Test that the correct model classes are returned"""
        settings.INSTALLED_APPS = ('django.contrib.flatpages',) 
        from django.contrib.flatpages.models import Site, FlatPage
        models = cache.get_models()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0], Site)
        self.assertEqual(models[1], FlatPage)
        self.assertTrue(cache.app_cache_ready())
    
    def test_app_mod(self):
        """
        Test that the correct model classes are returned if an
        app module is specified
        """
        settings.INSTALLED_APPS = ('django.contrib.flatpages',)
        from django.contrib.flatpages import models
        from django.contrib.flatpages.models import FlatPage
        rv = cache.get_models(app_mod=models)
        self.assertEqual(len(rv), 1)
        self.assertEqual(rv[0], FlatPage)
        self.assertTrue(cache.app_cache_ready())

    def test_include_auto_created(self):
        """Test that auto created models are included if specified"""
        settings.INSTALLED_APPS = ('django.contrib.flatpages',)
        from django.contrib.flatpages.models import Site, FlatPage
        models = cache.get_models(include_auto_created=True)
        self.assertEqual(len(models), 3)
        self.assertEqual(models[0], Site)
        self.assertEqual(models[1].__name__, 'FlatPage_sites')
        self.assertEqual(models[2], FlatPage)
        self.assertTrue(cache.app_cache_ready())

    def test_include_deferred(self):
        """TODO!"""

class GetModelTests(AppCacheTestCase):
    """Tests for the get_model function"""
    def test_get_model(self):
        """Test that the correct model is returned"""
        settings.INSTALLED_APPS = ('django.contrib.flatpages',)
        from django.contrib.flatpages.models import FlatPage
        self.assertEqual(cache.get_model('flatpages', 'FlatPage'), FlatPage)
        self.assertTrue(cache.app_cache_ready())

    def test_invalid(self):
        """Test that None is returned if an app/model does not exist"""
        self.assertEqual(cache.get_model('foo', 'bar'), None)
        self.assertTrue(cache.app_cache_ready())

    def test_without_seeding(self):
        """Test that None is returned if the cache is not seeded"""
        settings.INSTALLED_APPS = ('django.contrib.flatpages',)
        rv = cache.get_model('flatpages', 'FlatPage', seed_cache=False)
        self.assertEqual(rv, None)
        self.assertFalse(cache.app_cache_ready())

class RegisterModelsTests(AppCacheTestCase):
    """Tests for the register_models function"""
    def test_register_models(self):
        from django.contrib.flatpages.models import FlatPage, Site
        cache.register_models('foo', *(FlatPage, Site,))
        self.assertFalse(cache.app_cache_ready())
        rv = cache.get_models()
        self.assertEqual(len(rv), 4)
        self.assertEqual(rv[0], Site)
        self.assertEqual(rv[1], FlatPage)
        self.assertEqual(rv[2], FlatPage)
        self.assertEqual(rv[3], Site)

if __name__ == '__main__':
    unittest.main()

