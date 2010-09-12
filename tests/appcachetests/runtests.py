import copy
import sys
import unittest
import threading
from django.conf import settings
from django.utils.datastructures import SortedDict
from django.core.exceptions import ImproperlyConfigured
from django.core.apps import cache, MultipleInstancesReturned

# remove when tests are integrated into the django testsuite
settings.configure()


class AppCacheTestCase(unittest.TestCase):
    """
    TestCase that resets the AppCache after each test.
    """

    def setUp(self):
        self.old_installed_apps = settings.INSTALLED_APPS
        self.old_app_classes = settings.APP_CLASSES
        settings.APP_CLASSES = ()
        settings.INSTALLED_APPS = ()

    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps
        settings.APP_CLASSES = self.old_app_classes

        # The appcache imports models modules. We need to delete the
        # imported module from sys.modules after the test has run. 
        # If the module is imported again, the ModelBase.__new__ can 
        # register the models with the appcache anew.
        # Some models modules import other models modules (for example 
        # django.contrib.auth relies on django.contrib.contenttypes). 
        # To detect which model modules have been imported, we go through
        # all loaded model classes and remove their respective module 
        # from sys.modules
        for app in cache.unbound_models.itervalues():
            for name in app.itervalues():
                module = name.__module__
                if module in sys.modules:
                    del sys.modules[module]

        for app in cache.app_instances:
            for model in app.models:
                module = model.__module__
                if module in sys.modules:
                    del sys.modules[module]

        # we cannot copy() the whole cache.__dict__ in the setUp function
        # because thread.RLock is un(deep)copyable
        cache.unbound_models = {}
        cache.app_instances = []
        cache.installed_apps = []

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
        cache.load_app('nomodel_app')
        self.assertFalse(cache.app_cache_ready())
        cache.load_app('nomodel_app', can_postpone=True)
        self.assertFalse(cache.app_cache_ready())

class GetAppsTests(AppCacheTestCase):
    """Tests for the get_apps function"""

    def test_get_apps(self):
        """Test that the correct models modules are returned"""
        settings.INSTALLED_APPS = ('django.contrib.sites',
                                   'django.contrib.contenttypes',
                                   'django.contrib.auth',
                                   'django.contrib.flatpages',)
        apps = cache.get_apps()
        self.assertEqual(len(apps), 4)
        self.assertTrue(apps[0], 'django.contrib.auth.models')
        self.assertTrue(apps[1], 'django.contrib.flatpages.models')
        self.assertTrue(apps[2], 'django.contrib.sites.models')
        self.assertTrue(apps[3], 'django.contrib.contenttypes.models')
        self.assertTrue(cache.app_cache_ready())

    def test_empty_models(self):
        """Test that modules that don't contain models are not returned"""
        settings.INSTALLED_APPS = ('django.contrib.csrf',)
        self.assertEqual(cache.get_apps(), [])
        self.assertTrue(cache.app_cache_ready())

    def test_db_prefix_exception(self):
        """
        Test that an exception is raised if two app instances
        have the same db_prefix attribute
        """
        settings.APP_CLASSES = ('nomodel_app.MyApp', 'model_app.MyOtherApp',)
        self.assertRaises(ImproperlyConfigured, cache.get_apps)

class GetAppTests(AppCacheTestCase):
    """Tests for the get_app function"""

    def test_get_app(self):
        """Test that the correct module is returned"""
        settings.INSTALLED_APPS = ('django.contrib.contenttypes',
                                   'django.contrib.auth',)
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
        settings.INSTALLED_APPS = ('django.contrib.sites',
                                   'django.contrib.flatpages',) 
        models = cache.get_models()
        from django.contrib.flatpages.models import Site, FlatPage
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0], Site)
        self.assertEqual(models[1], FlatPage)
        self.assertTrue(cache.app_cache_ready())
    
    def test_app_mod(self):
        """
        Test that the correct model classes are returned if an
        app module is specified
        """
        settings.INSTALLED_APPS = ('django.contrib.sites',
                                   'django.contrib.flatpages',)
        # populate cache
        cache.get_app_errors()

        from django.contrib.flatpages import models
        from django.contrib.flatpages.models import FlatPage
        rv = cache.get_models(app_mod=models)
        self.assertEqual(len(rv), 1)
        self.assertEqual(rv[0], FlatPage)
        self.assertTrue(cache.app_cache_ready())

    def test_include_auto_created(self):
        """Test that auto created models are included if specified"""
        settings.INSTALLED_APPS = ('django.contrib.sites',
                                   'django.contrib.flatpages',)
        models = cache.get_models(include_auto_created=True)
        from django.contrib.flatpages.models import Site, FlatPage
        self.assertEqual(len(models), 3)
        self.assertEqual(models[0], Site)
        self.assertEqual(models[1], FlatPage)
        self.assertEqual(models[2].__name__, 'FlatPage_sites')
        self.assertTrue(cache.app_cache_ready())

class GetModelTests(AppCacheTestCase):
    """Tests for the get_model function"""

    def test_seeded(self):
        """
        Test that the correct model is returned when the cache is seeded
        """
        settings.INSTALLED_APPS = ('model_app',)
        rv = cache.get_model('model_app', 'Person')
        self.assertEqual(rv.__name__, 'Person')
        self.assertTrue(cache.app_cache_ready())

    def test_seeded_invalid(self):
        """
        Test that None is returned if a model was not registered
        with the seeded cache
        """
        rv = cache.get_model('model_app', 'Person')
        self.assertEqual(rv, None)
        self.assertTrue(cache.app_cache_ready())

    def test_unseeded(self):
        """
        Test that the correct model is returned when the cache is
        unseeded (but the model was registered using register_models)
        """
        from model_app.models import Person
        rv = cache.get_model('model_app', 'Person', seed_cache=False)
        self.assertEqual(rv.__name__, 'Person')
        self.assertFalse(cache.app_cache_ready())

    def test_unseeded_invalid(self):
        """
        Test that None is returned if a model was not registered
        with the unseeded cache
        """
        rv = cache.get_model('model_app', 'Person', seed_cache=False)
        self.assertEqual(rv, None)
        self.assertFalse(cache.app_cache_ready())

class LoadAppTests(AppCacheTestCase):
    """Tests for the load_app function"""

    def test_with_models(self):
        """
        Test that an app instance is created and the models
        module is returned
        """
        rv = cache.load_app('model_app')
        app = cache.app_instances[0]
        self.assertEqual(len(cache.app_instances), 1)
        self.assertEqual(app.name, 'model_app')
        self.assertEqual(app.models_module.__name__, 'model_app.models')
        self.assertEqual(rv.__name__, 'model_app.models')

    def test_without_models(self):
        """
        Test that an app instance is created when there are no models
        """
        rv = cache.load_app('nomodel_app')
        app = cache.app_instances[0]
        self.assertEqual(len(cache.app_instances), 1)
        self.assertEqual(app.name, 'nomodel_app')
        self.assertEqual(rv, None)

    def test_custom_app(self):
        """
        Test that a custom app instance is created if the function
        gets passed a custom app class
        """
        from nomodel_app import MyApp
        rv = cache.load_app('nomodel_app', False, MyApp)
        app = cache.app_instances[0]
        self.assertEqual(len(cache.app_instances), 1)
        self.assertEqual(app.name, 'nomodel_app')
        self.assertTrue(isinstance(app, MyApp))
        self.assertEqual(rv, None)

    def test_custom_models_path(self):
        """
        Test that custom models are imported correctly 
        """
        from nomodel_app import MyApp
        rv = cache.load_app('model_app', False, MyApp)
        app = cache.app_instances[0]
        self.assertEqual(app.models_module.__name__, 'model_app.models')
        self.assertEqual(rv.__name__, 'model_app.models')

    def test_twice(self):
        """
        Test that loading an app twice results in only one app instance
        """
        rv = cache.load_app('model_app')
        rv2 = cache.load_app('model_app')
        self.assertEqual(len(cache.app_instances), 1)
        self.assertEqual(rv.__name__, 'model_app.models')
        self.assertEqual(rv2.__name__, 'model_app.models')

    def test_importerror(self):
        """
        Test that an ImportError exception is raised if a package cannot
        be imported
        """
        self.assertRaises(ImportError, cache.load_app, 'garageland')

    def test_installed_apps(self):
        """
        Test that the installed_apps attribute is populated correctly
        """
        settings.APP_CLASSES = ('nomodel_app.MyApp',)
        settings.INSTALLED_APPS = ('model_app',)
        # populate cache
        cache.get_app_errors()
        self.assertEqual(cache.installed_apps, ['nomodel_app', 'model_app',])

class RegisterModelsTests(AppCacheTestCase):
    """Tests for the register_models function"""

    def test_seeded_cache(self):
        """
        Test that the models are attached to the correct app instance
        in a seeded cache
        """
        settings.INSTALLED_APPS = ('model_app',)
        cache.get_app_errors()
        self.assertTrue(cache.app_cache_ready())
        app_models = cache.app_instances[0].models
        self.assertEqual(len(app_models), 1)
        self.assertEqual(app_models[0].__name__, 'Person')

    def test_seeded_cache_invalid_app(self):
        """
        Test that an exception is raised if the cache is seeded and models
        are tried to be attached to an app instance that doesn't exist
        """
        settings.INSTALLED_APPS = ('model_app',)
        cache.get_app_errors()
        self.assertTrue(cache.app_cache_ready())
        from model_app.models import Person
        self.assertRaises(ImproperlyConfigured, cache.register_models,
                'model_app_NONEXISTENT', *(Person,))

    def test_unseeded_cache(self):
        """
        Test that models can be registered with an unseeded cache
        """
        from model_app.models import Person
        self.assertFalse(cache.app_cache_ready())
        self.assertEquals(cache.unbound_models['model_app']['person'], Person)

if __name__ == '__main__':
    unittest.main()

