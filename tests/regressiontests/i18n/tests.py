# coding: utf-8
import os
import misc

from django.conf import settings
from django.test import TestCase, client
from django.utils.translation import ugettext, activate, deactivate

regressions = ur"""
Format string interpolation should work with *_lazy objects.

>>> from django.utils.translation import ugettext, ugettext_lazy, activate, deactivate, gettext_lazy, to_locale
>>> s = ugettext_lazy('Add %(name)s')
>>> d = {'name': 'Ringo'}
>>> s % d
u'Add Ringo'
>>> activate('de')
>>> s % d
u'Ringo hinzuf\xfcgen'
>>> activate('pl')
>>> s % d
u'Dodaj Ringo'
>>> deactivate()

Tests the to_locale function and the special case of Serbian Latin (refs #12230 and r11299)

>>> to_locale('en-us')
'en_US'
>>> to_locale('sr-lat')
'sr_Lat'

Test the to_language function

>>> from django.utils.translation.trans_real import to_language
>>> to_language('en_US')
'en-us'
>>> to_language('sr_Lat')
'sr-lat'

It should be possible to compare *_lazy objects.

>>> s1 = ugettext_lazy('Add %(name)s')
>>> s == s1
True
>>> s2 = gettext_lazy('Add %(name)s')
>>> s3 = gettext_lazy('Add %(name)s')
>>> s2 == s3
True
>>> s == s2
True
>>> s4 = ugettext_lazy('Some other string')
>>> s == s4
False

unicode(string_concat(...)) should not raise a TypeError - #4796

>>> import django.utils.translation
>>> reload(django.utils.translation)
<module 'django.utils.translation' from ...>
>>> unicode(django.utils.translation.string_concat("dja", "ngo"))
u'django'

Translating a string requiring no auto-escaping shouldn't change the "safe"
status.

>>> from django.utils.safestring import mark_safe, SafeString
>>> s = mark_safe('Password')
>>> type(s)
<class 'django.utils.safestring.SafeString'>
>>> activate('de')
>>> type(ugettext(s))
<class 'django.utils.safestring.SafeUnicode'>
>>> deactivate()

>>> SafeString('a') + s
'aPassword'
>>> s + SafeString('a')
'Passworda'
>>> s + mark_safe('a')
'Passworda'
>>> mark_safe('a') + s
'aPassword'
>>> mark_safe('a') + mark_safe('s')
'as'
>>> print s
Password
"""

__test__ = {
    'regressions': regressions,
    'misc': misc.tests,
}

class ResolutionOrderI18NTests(TestCase):

    def setUp(self):
        from django.utils.translation import trans_real
        # Okay, this is brutal, but we have no other choice to fully reset
        # the translation framework
        trans_real._active = {}
        trans_real._translations = {}
        activate('de')

    def tearDown(self):
        deactivate()

    def assertUgettext(self, msgid, msgstr):
        result = ugettext(msgid)
        self.assert_(msgstr in result, ("The string '%s' isn't in the "
            "translation of '%s'; the actual result is '%s'." % (msgstr, msgid, result)))

class AppResolutionOrderI18NTests(ResolutionOrderI18NTests):

    def setUp(self):
        self.old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ['regressiontests.i18n.resolution']
        super(AppResolutionOrderI18NTests, self).setUp()

    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps
        super(AppResolutionOrderI18NTests, self).tearDown()

    def test_app_translation(self):
        self.assertUgettext('Date/time', 'APP')

class LocalePathsResolutionOrderI18NTests(ResolutionOrderI18NTests):

    def setUp(self):
        self.old_locale_paths = settings.LOCALE_PATHS
        settings.LOCALE_PATHS += (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'other', 'locale'),)
        super(LocalePathsResolutionOrderI18NTests, self).setUp()

    def tearDown(self):
        settings.LOCALE_PATHS = self.old_locale_paths
        super(LocalePathsResolutionOrderI18NTests, self).tearDown()

    def test_locale_paths_translation(self):
        self.assertUgettext('Date/time', 'LOCALE_PATHS')

class ProjectResolutionOrderI18NTests(ResolutionOrderI18NTests):

    def setUp(self):
        self.old_settings_module = settings.SETTINGS_MODULE
        settings.SETTINGS_MODULE = 'regressiontests'
        super(ProjectResolutionOrderI18NTests, self).setUp()

    def tearDown(self):
        settings.SETTINGS_MODULE = self.old_settings_module
        super(ProjectResolutionOrderI18NTests, self).tearDown()

    def test_project_translation(self):
        self.assertUgettext('Date/time', 'PROJECT')

    def test_project_override_app_translation(self):
        old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ['regressiontests.i18n.resolution']
        self.assertUgettext('Date/time', 'PROJECT')
        settings.INSTALLED_APPS = old_installed_apps

    def test_project_override_locale_paths_translation(self):
        old_locale_paths = settings.LOCALE_PATHS
        settings.LOCALE_PATHS += (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'other', 'locale'),)
        self.assertUgettext('Date/time', 'PROJECT')
        settings.LOCALE_PATHS = old_locale_paths

class DjangoFallbackResolutionOrderI18NTests(ResolutionOrderI18NTests):

    def test_django_fallback(self):
        self.assertUgettext('Date/time', 'Datum/Zeit')
