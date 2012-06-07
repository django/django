from StringIO import StringIO
from django.test import TestCase
import os
from django.core.management.commands import compilemessages
from django.conf import settings

class CompileMessagesFunctionTestCase(TestCase):
    MO_FILE_DE = None
    MO_FILE_FR = None
    
    def setUp(self):
        self._old_locale_paths = settings.LOCALE_PATHS
        self.stderr = StringIO()
        self.localedir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'locale'
        )
        settings.LOCALE_PATHS = [self.localedir]
        self.MO_FILE_DE = os.path.join(self.localedir, 'de/LC_MESSAGES/django.mo')
        self.MO_FILE_FR = os.path.join(self.localedir, 'fr/LC_MESSAGES/django.mo')
        
    def tearDown(self):
        settings.LOCALE_PATHS = self._old_locale_paths
        self.stderr.close()
        self._rmfile(os.path.join(self.localedir, self.MO_FILE_DE))
        self._rmfile(os.path.join(self.localedir, self.MO_FILE_FR))
        
    def _rmfile(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)
            
    def test_one_locale(self):
        command = compilemessages.Command()
        command.execute(locale='de', stderr=self.stderr)
        
        self.assertTrue(os.path.exists(self.MO_FILE_DE))
        
    def test_multiple_locales(self):
        command = compilemessages.Command()
        command.execute(locale=['de', 'fr'], stderr=self.stderr)
        
        self.assertTrue(os.path.exists(self.MO_FILE_DE))
        self.assertTrue(os.path.exists(self.MO_FILE_FR))