from copy import deepcopy

from django.core.checks.templates import E001
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
