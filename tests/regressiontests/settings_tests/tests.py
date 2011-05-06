from django.conf import settings
from django.test import TestCase

class SettingsTests(TestCase):

    def test_override(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_change(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test2'
        self.assertEqual('test', settings.TEST)
        del settings.TEST

    def test_override_doesnt_leak(self):
        self.assertRaises(AttributeError, getattr, settings, 'TEST')
        with self.settings(TEST='override'):
            self.assertEqual('override', settings.TEST)
            settings.TEST = 'test'
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    #
    # Regression tests for #10130: deleting settings.
    #

    def test_settings_delete(self):
        settings.TEST = 'test'
        self.assertEqual('test', settings.TEST)
        del settings.TEST
        self.assertRaises(AttributeError, getattr, settings, 'TEST')

    def test_settings_delete_wrapped(self):
        self.assertRaises(TypeError, delattr, settings, '_wrapped')



class TrailingSlashURLTests(TestCase):
    settings_module = settings

    def setUp(self):
        self._original_media_url = self.settings_module.MEDIA_URL

    def tearDown(self):
        self.settings_module.MEDIA_URL = self._original_media_url

    def test_blank(self):
        """
        If blank, no DeprecationWarning error will be raised, even though it
        doesn't end in a slash.
        """
        self.settings_module.MEDIA_URL = ''
        self.assertEqual('', self.settings_module.MEDIA_URL)

    def test_end_slash(self):
        """
        MEDIA_URL works if you end in a slash.
        """
        self.settings_module.MEDIA_URL = '/foo/'
        self.assertEqual('/foo/', self.settings_module.MEDIA_URL)

        self.settings_module.MEDIA_URL = 'http://media.foo.com/'
        self.assertEqual('http://media.foo.com/',
                         self.settings_module.MEDIA_URL)

    def test_no_end_slash(self):
        """
        MEDIA_URL raises an DeprecationWarning error if it doesn't end in a
        slash.
        """
        import warnings
        warnings.filterwarnings('error', 'If set, MEDIA_URL must end with a slash', DeprecationWarning)

        def setattr_settings(settings_module, attr, value):
            setattr(settings_module, attr, value)

        self.assertRaises(DeprecationWarning, setattr_settings,
                          self.settings_module, 'MEDIA_URL', '/foo')

        self.assertRaises(DeprecationWarning, setattr_settings,
                          self.settings_module, 'MEDIA_URL',
                          'http://media.foo.com')

    def test_double_slash(self):
        """
        If a MEDIA_URL ends in more than one slash, presume they know what
        they're doing.
        """
        self.settings_module.MEDIA_URL = '/stupid//'
        self.assertEqual('/stupid//', self.settings_module.MEDIA_URL)

        self.settings_module.MEDIA_URL = 'http://media.foo.com/stupid//'
        self.assertEqual('http://media.foo.com/stupid//',
                         self.settings_module.MEDIA_URL)
