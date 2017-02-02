from copy import copy, deepcopy

from django.core.checks.templates import E001, E002
from django.test import SimpleTestCase
from django.test.utils import override_settings


class CheckTemplateSettingsAppDirsTest(SimpleTestCase):
    TEMPLATES_APP_DIRS_AND_LOADERS = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'APP_DIRS': True,
            'OPTIONS': {
                'loaders': ['django.template.loaders.filesystem.Loader'],
            },
        },
    ]

    @property
    def func(self):
        from django.core.checks.templates import check_setting_app_dirs_loaders
        return check_setting_app_dirs_loaders

    @override_settings(TEMPLATES=TEMPLATES_APP_DIRS_AND_LOADERS)
    def test_app_dirs_and_loaders(self):
        """
        Error if template loaders are specified and APP_DIRS is True.
        """
        self.assertEqual(self.func(None), [E001])

    def test_app_dirs_removed(self):
        TEMPLATES = deepcopy(self.TEMPLATES_APP_DIRS_AND_LOADERS)
        del TEMPLATES[0]['APP_DIRS']
        with self.settings(TEMPLATES=TEMPLATES):
            self.assertEqual(self.func(None), [])

    def test_loaders_removed(self):
        TEMPLATES = deepcopy(self.TEMPLATES_APP_DIRS_AND_LOADERS)
        del TEMPLATES[0]['OPTIONS']['loaders']
        with self.settings(TEMPLATES=TEMPLATES):
            self.assertEqual(self.func(None), [])


class CheckTemplateStringIfInvalidTest(SimpleTestCase):
    TEMPLATES_STRING_IF_INVALID = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'OPTIONS': {
                'string_if_invalid': False,
            },
        },
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'OPTIONS': {
                'string_if_invalid': 42,
            },
        },
    ]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.error1 = copy(E002)
        cls.error2 = copy(E002)
        string_if_invalid1 = cls.TEMPLATES_STRING_IF_INVALID[0]['OPTIONS']['string_if_invalid']
        string_if_invalid2 = cls.TEMPLATES_STRING_IF_INVALID[1]['OPTIONS']['string_if_invalid']
        cls.error1.msg = cls.error1.msg.format(string_if_invalid1, type(string_if_invalid1).__name__)
        cls.error2.msg = cls.error2.msg.format(string_if_invalid2, type(string_if_invalid2).__name__)

    @property
    def func(self):
        from django.core.checks.templates import check_string_if_invalid_is_string
        return check_string_if_invalid_is_string

    @override_settings(TEMPLATES=TEMPLATES_STRING_IF_INVALID)
    def test_string_if_invalid_not_string(self):
        self.assertEqual(self.func(None), [self.error1, self.error2])

    def test_string_if_invalid_first_is_string(self):
        TEMPLATES = deepcopy(self.TEMPLATES_STRING_IF_INVALID)
        TEMPLATES[0]['OPTIONS']['string_if_invalid'] = 'test'
        with self.settings(TEMPLATES=TEMPLATES):
            self.assertEqual(self.func(None), [self.error2])

    def test_string_if_invalid_both_are_strings(self):
        TEMPLATES = deepcopy(self.TEMPLATES_STRING_IF_INVALID)
        TEMPLATES[0]['OPTIONS']['string_if_invalid'] = 'test'
        TEMPLATES[1]['OPTIONS']['string_if_invalid'] = 'test'
        with self.settings(TEMPLATES=TEMPLATES):
            self.assertEqual(self.func(None), [])

    def test_string_if_invalid_not_specified(self):
        TEMPLATES = deepcopy(self.TEMPLATES_STRING_IF_INVALID)
        del TEMPLATES[1]['OPTIONS']['string_if_invalid']
        with self.settings(TEMPLATES=TEMPLATES):
            self.assertEqual(self.func(None), [self.error1])
