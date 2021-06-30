from mango.core.exceptions import ImproperlyConfigured
from mango.template import engines
from mango.test import SimpleTestCase, override_settings


class TemplateUtilsTests(SimpleTestCase):

    @override_settings(TEMPLATES=[{'BACKEND': 'raise.import.error'}])
    def test_backend_import_error(self):
        """
        Failing to import a backend keeps raising the original import error
        (#24265).
        """
        with self.assertRaisesMessage(ImportError, "No module named 'raise"):
            engines.all()
        with self.assertRaisesMessage(ImportError, "No module named 'raise"):
            engines.all()

    @override_settings(TEMPLATES=[{
        'BACKEND': 'mango.template.backends.mango.MangoTemplates',
        # Incorrect: APP_DIRS and loaders are mutually incompatible.
        'APP_DIRS': True,
        'OPTIONS': {'loaders': []},
    }])
    def test_backend_improperly_configured(self):
        """
        Failing to initialize a backend keeps raising the original exception
        (#24265).
        """
        msg = 'app_dirs must not be set when loaders is defined.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            engines.all()
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            engines.all()

    @override_settings(TEMPLATES=[{
        'BACKEND': 'mango.template.backends.mango.MangoTemplates',
    }, {
        'BACKEND': 'mango.template.backends.mango.MangoTemplates',
    }])
    def test_backend_names_must_be_unique(self):
        msg = (
            "Template engine aliases aren't unique, duplicates: mango. Set "
            "a unique NAME for each engine in settings.TEMPLATES."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            engines.all()
