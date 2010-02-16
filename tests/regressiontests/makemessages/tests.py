import os
import re
import shutil
from django.test import TestCase
from django.core import management

LOCALE='de'

class ExtractorTests(TestCase):

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(__file__))

    def _rmrf(self, dname):
        if os.path.commonprefix([self.test_dir, os.path.abspath(dname)]) != self.test_dir:
            return
        shutil.rmtree(dname)

    def tearDown(self):
        os.chdir(self.test_dir)
        try:
            self._rmrf('locale/%s' % LOCALE)
        except OSError:
            pass
        os.chdir(self._cwd)

    def assertMsgId(self, msgid, s):
        return self.assert_(re.search('^msgid "%s"' % msgid, s, re.MULTILINE))


class JavascriptExtractorTests(ExtractorTests):

    PO_FILE='locale/%s/LC_MESSAGES/djangojs.po' % LOCALE

    def test_javascript_literals(self):
        os.chdir(self.test_dir)
        management.call_command('makemessages', domain='djangojs', locale=LOCALE, verbosity=0)
        self.assert_(os.path.exists(self.PO_FILE))
        po_contents = open(self.PO_FILE, 'r').read()
        self.assertMsgId('This literal should be included.', po_contents)
        self.assertMsgId('This one as well.', po_contents)
