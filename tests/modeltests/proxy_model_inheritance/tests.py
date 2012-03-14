"""
XX. Proxy model inheritance

Proxy model inheritance across apps can result in syncdb not creating the table
for the proxied model (as described in #12286).  This test creates two dummy
apps and calls syncdb, then verifies that the table has been created.
"""

from __future__ import absolute_import

import os
import sys

from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import cache, load_app
from django.test import TransactionTestCase
from django.test.utils import override_settings


# @override_settings(INSTALLED_APPS=('app1', 'app2'))
class ProxyModelInheritanceTests(TransactionTestCase):

    def setUp(self):
        self.old_sys_path = sys.path[:]
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        map(load_app, settings.INSTALLED_APPS)

    def tearDown(self):
        sys.path = self.old_sys_path
        del cache.app_store[cache.app_labels['app1']]
        del cache.app_store[cache.app_labels['app2']]
        del cache.app_labels['app1']
        del cache.app_labels['app2']
        del cache.app_models['app1']
        del cache.app_models['app2']

    def test_table_exists(self):
        call_command('syncdb', verbosity=0)
        from .app1.models import ProxyModel
        from .app2.models import NiceModel
        self.assertEqual(NiceModel.objects.all().count(), 0)
        self.assertEqual(ProxyModel.objects.all().count(), 0)

ProxyModelInheritanceTests = override_settings(INSTALLED_APPS=('app1', 'app2'))(ProxyModelInheritanceTests)
