from django.apps import apps
from django.core import checks
from django.test import SimpleTestCase, override_settings


class RemovedSettingsCheckTests(SimpleTestCase):
    @override_settings(TRANSACTIONS_MANAGED=True)
    def test_check_removed_settings(self):
        all_issues = checks.run_checks(app_configs=apps.get_app_configs())

        self.assertGreater(len(all_issues), 0)

        self.assertIn(
            checks.Warning(
                "The 'TRANSACTIONS_MANAGED' setting was removed and its use "
                "is not recommended.",
                hint="Please refer to the documentation and remove/replace "
                "this setting.",
                obj="TRANSACTIONS_MANAGED",
                id="settings.W001",
            ),
            all_issues,
        )
