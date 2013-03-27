from __future__ import absolute_import

import os
import sys

from django.db.models.loading import cache, _initial_appcache_state
from django.test import TestCase
from django.test.utils import override_settings
from django.conf import settings

from django.utils._os import upath


class ModelLazyLoading(TestCase):
    """
    Test that related models that have not yet been imported gets
    imported when they are needed.

    This test case will clear the global app cache during test runs to
    simulate the import process, and then reset it to not mess up other
    tests.

    If more tests are to be added, there need to be more apps than
    `app1` and `app2`, since the model modules must not be cached in
    sys.modules.

    See https://code.djangoproject.com/ticket/20143
    """

    def setUp(self):
        self.old_sys_path = sys.path[:]
        self.old_app_cache = dict(cache.__dict__)

        sys.path.append(os.path.dirname(os.path.abspath(upath(__file__))))
        cache.__dict__.update(_initial_appcache_state())

    def tearDown(self):
        sys.path = self.old_sys_path
        cache.__dict__.update(self.old_app_cache)

    def assertAppIsImported(self, app_name):
        self.assertTrue(any(x for x in sys.modules.keys() if (app_name in x)),
                        '%s must not already be imported' % app_name)

    def assertAppIsNotImported(self, app_name):
        self.assertFalse(any(x for x in sys.modules.keys() if (app_name in x)),
                         '%s must be imported' % app_name)

    @override_settings(INSTALLED_APPS=('lazyload_a', 'lazyload_b'))
    def test_instantiate_model_a(self):
        """
        Make sure that the dependency on App2Model gets resolved so that
        App1Model can be instantiated.
        """
        # Make sure the models are not already loaded, it would make the
        # test useluss
        self.assertAppIsNotImported('lazyload_a')
        self.assertAppIsNotImported('lazyload_b')

        from .lazyload_a.models import A

        # This should force lazyload_b.models to be imported and loaded
        # to app cache
        A()

        self.assertAppIsImported('lazyload_a')
        self.assertAppIsImported('lazyload_b')
