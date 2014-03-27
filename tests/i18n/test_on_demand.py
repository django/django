import os
import unittest
import shutil

from django.core.management.utils import find_command
from django.test import SimpleTestCase, override_settings
from django.utils._os import upath
from django.utils import translation
from django.utils.translation import ugettext, trans_real
from django.utils.translation.trans_real import needs_compilation
from threading import local

import gettext as gettext_module

test_dir = os.path.abspath(
                os.path.join(os.path.dirname(upath(__file__)),
                'on_demand'))
test_locale = [os.path.join(test_dir, 'locale')]

has_msgfmt = find_command('msgfmt')


@unittest.skipUnless(has_msgfmt, 'msgfmt is mandatory for compilation tests')
class OnDemandCompilationTests(SimpleTestCase):

    def setUp(self):
        self._cwd = os.getcwd()
        self.addCleanup(os.chdir, self._cwd)
        os.chdir(test_dir)

    def rmfile(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)


class MissingMOTest(OnDemandCompilationTests):
    PO_FILE = 'locale/xx/LC_MESSAGES/django.po'
    MO_FILE = 'locale/xx/LC_MESSAGES/django.mo'
    BACKUP_FILE = 'locale/xx/LC_MESSAGES/backup.po'
    NEW_FILE = 'locale/xx/LC_MESSAGES/replacement.po'

    def tearDown(self):
        os.remove(self.MO_FILE)

    @override_settings(LOCALE_PATHS=test_locale, DEBUG=True)
    def test_no_mo(self):
        self.assertTrue(os.path.exists(self.PO_FILE))
        self.assertFalse(os.path.exists(self.MO_FILE))

        trans_real._active = local()
        trans_real._translations = {}
        with translation.override('xx'):
            self.assertEqual(ugettext("Anything"), "Find Value")
        self.assertTrue(os.path.exists(self.MO_FILE))


class ReplacementFileTest(OnDemandCompilationTests):
    PO_FILE = 'locale/xx/LC_MESSAGES/django.po'
    MO_FILE = 'locale/xx/LC_MESSAGES/django.mo'
    BACKUP_FILE = 'locale/xx/LC_MESSAGES/backup.po'
    NEW_FILE = 'locale/xx/LC_MESSAGES/replacement.po'

    def tearDown(self):
        os.remove(self.MO_FILE)
        shutil.copyfile(self.BACKUP_FILE, self.PO_FILE)

    @override_settings(LOCALE_PATHS=test_locale, DEBUG=True)
    def test_new_values(self):
        trans_real._active = local()
        trans_real._translations = {}
        with translation.override('xx'):
            self.assertEqual(ugettext("Anything"), "Find Value")

        shutil.copyfile(self.NEW_FILE, self.PO_FILE)
        with translation.override('xx'):
            self.assertEqual(ugettext("Anything"), "Find new Value")


class OldMOTest(OnDemandCompilationTests):
    PO_FILE = 'locale/ww/LC_MESSAGES/django.po'
    MO_FILE = 'locale/ww/LC_MESSAGES/django.mo'

    @override_settings(LOCALE_PATHS=test_locale, DEBUG=True)
    def test_old_mo(self):
        # 'touch' the .po file, to indicate changes
        os.utime(self.PO_FILE, None)

        # Get the current time on the .mo file, as the basis for testing
        starting_mtime = os.path.getmtime(self.MO_FILE)

        with translation.override('ww'):
            self.assertEqual(ugettext("Anything"), "Find Value")

        ending_mtime = os.path.getmtime(self.MO_FILE)

        self.assertTrue(ending_mtime > starting_mtime)


class NeedsTranslationTest(SimpleTestCase):
    PO_FILE = 'locale/yy/LC_MESSAGES/'
    ROOT_PATH = test_locale[0]

    # These 3 test missing .mo files
    @override_settings(DEBUG=True)
    def test_debug_true(self):
        self.assertTrue(needs_compilation('django', self.ROOT_PATH, 'yy'))

    @override_settings(DEBUG=False)
    def test_debug_false(self):
        self.assertFalse(needs_compilation('django', self.ROOT_PATH, 'yy'))

    @override_settings(DEBUG=False, I18N_RELOAD_ON_CHANGE=True)
    def test_i18n_extra_config(self):
        self.assertTrue(needs_compilation('django', self.ROOT_PATH, 'yy'))

    @override_settings(DEBUG=True)
    def test_missing_po_file(self):
        self.assertFalse(needs_compilation('not_found', self.ROOT_PATH, 'yy'))

    @override_settings(DEBUG=True)
    def test_newer_mo_file(self):
        base_path = os.path.join(test_dir, 'locale', 'yy', 'LC_MESSAGES')
        mo_path = os.path.join(base_path, 't1.mo')
        po_path = os.path.join(base_path, 't1.po')

        open(po_path, 'w').close()
        open(mo_path, 'w').close()

        # Arbitrary, made up times
        os.utime(po_path, (100, 100))
        os.utime(mo_path, (200, 200))
        self.assertFalse(needs_compilation('t1', self.ROOT_PATH, 'yy'))

    @override_settings(DEBUG=True)
    def test_newer_po_file(self):
        base_path = os.path.join(test_dir, 'locale', 'yy', 'LC_MESSAGES')
        mo_path = os.path.join(base_path, 't1.mo')
        po_path = os.path.join(base_path, 't1.po')

        open(po_path, 'w').close()
        open(mo_path, 'w').close()

        os.utime(po_path, (200, 200))
        os.utime(mo_path, (100, 100))
        self.assertTrue(needs_compilation('t1', self.ROOT_PATH, 'yy'))
