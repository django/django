from django.core.checks.templates import E001
from django.test import SimpleTestCase
from django.test.utils import override_settings

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]


class CheckTemplateSettingsTest(SimpleTestCase):
    @property
    def func(self):
        from django.core.checks.templates import check_setting_app_dirs_loaders
        return check_setting_app_dirs_loaders

    @override_settings(TEMPLATES=TEMPLATES)
    def test_app_dirs_and_loaders(self):
        """
        Error if template loaders are specified and APP_DIRS is `True`
        """
        self.assertEqual(self.func(None), [E001])
