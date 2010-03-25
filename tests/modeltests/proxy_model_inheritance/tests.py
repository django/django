"""
XX. Proxy model inheritance

Proxy model inheritance across apps can result in syncdb not creating the table
for the proxied model (as described in #12286).  This test creates two dummy
apps and calls syncdb, then verifies that the table has been created.
"""

import os
import sys

from django.conf import settings, Settings
from django.core.management import call_command
from django.db.models.loading import load_app
from django.test import TransactionTestCase

class ProxyModelInheritanceTests(TransactionTestCase):

    def setUp(self):
        self.old_sys_path = sys.path
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        self.old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = ('app1', 'app2')
        map(load_app, settings.INSTALLED_APPS)
        call_command('syncdb', verbosity=0)
        from app1.models import ProxyModel
        from app2.models import NiceModel
        global ProxyModel, NiceModel

    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps
        sys.path = self.old_sys_path

    def test_table_exists(self):
        self.assertEquals(NiceModel.objects.all().count(), 0)
        self.assertEquals(ProxyModel.objects.all().count(), 0)
