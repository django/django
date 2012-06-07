import os
from .extraction import ExtractorTests
from django.core import management

class MakeMessagesFunctionTestCase(ExtractorTests):
    PO_FILE_PT = 'locale/pt/LC_MESSAGES/django.po'
    PO_FILE_DE = 'locale/de/LC_MESSAGES/django.po'
    LOCALES = ['pt', 'de', 'ch']
    
    
    def tearDown(self):
        os.chdir(self.test_dir)
        for locale in self.LOCALES:
            try:
                self._rmrf('locale/%s' % locale)
            except OSError:
                pass
        os.chdir(self._cwd)
    
    def test_multiple_locales(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale=['pt','de'], verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_PT))
        self.assertTrue(os.path.exists(self.PO_FILE_DE))
    
    def test_comma_separated_locales(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', locale='pt,de,ch', verbosity=0)
        self.assertTrue(os.path.exists(self.PO_FILE_PT))
        self.assertTrue(os.path.exists(self.PO_FILE_DE))