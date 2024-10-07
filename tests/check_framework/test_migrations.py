from django.core import checks
from django.core.checks import Error
from django.core.management.commands.makemigrations import (
    Command as MakeMigrationsCommand,
)
from django.core.management.commands.migrate import Command as MigrateCommand
from django.test import SimpleTestCase
from django.test.utils import isolate_apps, override_settings, override_system_checks


@isolate_apps("check_framework.custom_commands_app", attr_name="apps")
@override_settings(INSTALLED_APPS=["check_framework.custom_commands_app"])
@override_system_checks(
    [checks.migrations.migrate_and_migrations_share_same_autodetector]
)
class MigrationsCheckTests(SimpleTestCase):
    def test_migrate_and_makemigrations_cant_share_same_autodetector(self):
        class NewMigrateCommand(MigrateCommand):
            pass

        class NewMakeMigrationsCommand(MakeMigrationsCommand):
            autodetector_class = int

        expected_error = Error(
            "Migrate and makemigrations don't share the same autodetector class. ",
            hint=(
                "makemigrations.Command.autodetector_class is {}, but "
                "migrate.Command.autodetector_class is {}."
            ).format(
                NewMakeMigrationsCommand.autodetector_class.__name__,
                NewMigrateCommand.autodetector_class.__name__,
            ),
            id="migrations.E001",
        )

        self.assertEqual(
            checks.run_checks(app_configs=self.apps.get_app_configs()),
            [expected_error],
        )
