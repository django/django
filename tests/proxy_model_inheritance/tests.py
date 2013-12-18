from __future__ import unicode_literals

import os
import sys

from django.core.apps import app_cache
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils._os import upath

from .models import (ConcreteModel, ConcreteModelSubclass,
    ConcreteModelSubclassProxy)


@override_settings(INSTALLED_APPS=('app1', 'app2'))
class ProxyModelInheritanceTests(TransactionTestCase):
    """
    Proxy model inheritance across apps can result in migrate not creating the table
    for the proxied model (as described in #12286).  This test creates two dummy
    apps and calls migrate, then verifies that the table has been created.
    """
    available_apps = ['app1', 'app2']

    def setUp(self):
        self.old_sys_path = sys.path[:]
        sys.path.append(os.path.dirname(os.path.abspath(upath(__file__))))
        self._with_app1 = app_cache._begin_with_app('app1')
        self._with_app2 = app_cache._begin_with_app('app2')

    def tearDown(self):
        app_cache._end_with_app(self._with_app1)
        app_cache._end_with_app(self._with_app2)
        sys.path = self.old_sys_path

    def test_table_exists(self):
        call_command('migrate', verbosity=0)
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
