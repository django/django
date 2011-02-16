from os.path import join, normpath, abspath, dirname
import warnings

import django
from django.conf import settings
from django.test.utils import get_warnings_state, restore_warnings_state
from django.utils.translation import _trans
from django.utils.unittest import TestCase


class DeprecationWarningTests(TestCase):

    def setUp(self):
        self.warning_state = get_warnings_state()
        self.old_settings_module = settings.SETTINGS_MODULE
        settings.SETTINGS_MODULE = 'regressiontests'
        self.old_locale_paths = settings.LOCALE_PATHS

    def tearDown(self):
        restore_warnings_state(self.warning_state)
        settings.SETTINGS_MODULE = self.old_settings_module
        settings.LOCALE_PATHS = self.old_locale_paths

    def test_warn_if_project_has_locale_subdir(self):
        """Test that PendingDeprecationWarning is generated when a deprecated project level locale/ subdir is present."""
        project_path = join(dirname(abspath(__file__)), '..')
        warnings.filterwarnings('error',
                "Translations in the project directory aren't supported anymore\. Use the LOCALE_PATHS setting instead\.",
                PendingDeprecationWarning)
        _trans.__dict__ = {}
        self.assertRaises(PendingDeprecationWarning, django.utils.translation.ugettext, 'Time')

    def test_no_warn_if_project_and_locale_paths_overlap(self):
        """Test that PendingDeprecationWarning isn't generated when a deprecated project level locale/ subdir is also included in LOCALE_PATHS."""
        project_path = join(dirname(abspath(__file__)), '..')
        settings.LOCALE_PATHS += (normpath(join(project_path, 'locale')),)
        warnings.filterwarnings('error',
                "Translations in the project directory aren't supported anymore\. Use the LOCALE_PATHS setting instead\.",
                PendingDeprecationWarning)
        _trans.__dict__ = {}
        try:
            django.utils.translation.ugettext('Time')
        except PendingDeprecationWarning:
            self.fail("PendingDeprecationWarning shouldn't be raised when settings/project locale and a LOCALE_PATHS member point to the same file system location.")
