from django.core import checks
from django.core.checks import Error
from django.test import SimpleTestCase
from django.test.utils import isolate_apps, override_settings, override_system_checks


@isolate_apps("check_framework.custom_commands_app", attr_name="apps")
@override_settings(INSTALLED_APPS=["check_framework.custom_commands_app"])
@override_system_checks([checks.commands.migrate_and_makemigrations_autodetector])
class CommandCheckTests(SimpleTestCase):
    def test_migrate_and_makemigrations_autodetector_different(self):
        expected_error = Error(
            "The migrate and makemigrations commands must have the same "
            "autodetector.",
            hint=(
                "makemigrations.Command.autodetector is int, but "
                "migrate.Command.autodetector is MigrationAutodetector."
            ),
            id="commands.E001",
        )

        self.assertEqual(
            checks.run_checks(app_configs=self.apps.get_app_configs()),
            [expected_error],
        )
