import os
import sys
from StringIO import StringIO

from django.conf import settings
from django.core.management import call_command
from django.db.models.loading import load_app
from django.test import TestCase

class InspectDBTestCase(TestCase):
    
    def setUp(self):
        self.old_sys_path = sys.path[:]
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        self.old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = ('bug',)
        map(load_app, settings.INSTALLED_APPS)
        call_command('syncdb', verbosity=0)
        
    def test_attribute_name_not_python_keyword(self):
        out = StringIO()
        call_command('inspectdb', stdout=out)
        error_message = "inspectdb generated an attribute name which is a python keyword"
        self.assertNotIn("from = models.ForeignKey(BugPeople)", out.getvalue(), msg=error_message)
        out.close()
        
    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps
        sys.path = self.old_sys_path
