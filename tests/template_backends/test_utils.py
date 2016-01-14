from django.core.exceptions import ImproperlyConfigured
from django.template import engines
from django.test import SimpleTestCase, override_settings


class TemplateStringsTests(SimpleTestCase):

    @override_settings(TEMPLATES=[{
        'BACKEND': 'raise.import.error',
    }])
    def test_backend_import_error(self):
        """
        Failing to import a backend keeps raising the original import error.

        Regression test for #24265.
        """
        with self.assertRaises(ImportError):
            engines.all()
        with self.assertRaises(ImportError):
            engines.all()

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Incorrect: APP_DIRS and loaders are mutually incompatible.
        'APP_DIRS': True,
        'OPTIONS': {'loaders': []},
    }])
    def test_backend_improperly_configured(self):
        """
        Failing to initialize a backend keeps raising the original exception.

        Regression test for #24265.
        """
        with self.assertRaises(ImproperlyConfigured):
            engines.all()
        with self.assertRaises(ImproperlyConfigured):
            engines.all()

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    }, {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    }])
    def test_backend_names_must_be_unique(self):
        with self.assertRaises(ImproperlyConfigured):
            engines.all()
