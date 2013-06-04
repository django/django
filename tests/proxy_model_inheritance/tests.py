from __future__ import absolute_import

import os
import sys

from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import cache, load_app
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils._os import upath

from .models import (ConcreteModel, ConcreteModelSubclass,
    ConcreteModelSubclassProxy)


@override_settings(INSTALLED_APPS=('app1', 'app2'))
class ProxyModelInheritanceTests(TransactionTestCase):
    """
    Proxy model inheritance across apps can result in syncdb not creating the table
    for the proxied model (as described in #12286).  This test creates two dummy
    apps and calls syncdb, then verifies that the table has been created.
    """

    available_apps = []

    def setUp(self):
        self.old_sys_path = sys.path[:]
        sys.path.append(os.path.dirname(os.path.abspath(upath(__file__))))
        for app in settings.INSTALLED_APPS:
            load_app(app)

    def tearDown(self):
        sys.path = self.old_sys_path
        del cache.app_store[cache.app_labels['app1']]
        del cache.app_store[cache.app_labels['app2']]
        del cache.app_labels['app1']
        del cache.app_labels['app2']
        del cache.app_models['app1']
        del cache.app_models['app2']

    def test_table_exists(self):
        try:
            cache.set_available_apps(settings.INSTALLED_APPS)
            call_command('syncdb', verbosity=0)
        finally:
            cache.unset_available_apps()
        from .app1.models import ProxyModel
        from .app2.models import NiceModel
        self.assertEqual(NiceModel.objects.all().count(), 0)
        self.assertEqual(ProxyModel.objects.all().count(), 0)


class MultiTableInheritanceProxyTest(TestCase):

    def test_model_subclass_proxy(self):
        """
        Deleting an instance of a model proxying a multi-table inherited
        subclass should cascade delete down the whole inheritance chain (see
        #18083).

        """
        instance = ConcreteModelSubclassProxy.objects.create()
        instance.delete()
        self.assertEqual(0, ConcreteModelSubclassProxy.objects.count())
        self.assertEqual(0, ConcreteModelSubclass.objects.count())
        self.assertEqual(0, ConcreteModel.objects.count())
