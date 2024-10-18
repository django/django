from django.apps import apps
from django.core import checks
from django.test import SimpleTestCase, override_settings


class SettingsDeprecationCheckTests(SimpleTestCase):
    @override_settings(TRANSACTIONS_MANAGED=True)
    def test_check_deprecated_settings(self):
        all_issues = checks.run_checks(app_configs=apps.get_app_configs())

        self.assertGreater(len(all_issues), 0)

        self.assertIn(
            checks.Warning(
                "You still use 'TRANSACTIONS_MANAGED' in your Django settings "
                "file. This attribute is deprecated.",
                hint="Please refer to the documentation and remove/replace "
                "this attribute.",
                id="settings.W001",
            ),
            all_issues,
        )
