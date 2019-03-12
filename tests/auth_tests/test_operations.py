from django.conf import settings
from django.core.management import call_command
from django.test import TransactionTestCase, override_settings


@override_settings(
    MIGRATION_MODULES=dict(
        settings.MIGRATION_MODULES,
        auth="django.contrib.auth.migrations",
        contenttypes="django.contrib.contenttypes.migrations",
        auth_tests="auth_tests.operations_migrations",
    )
)
class RenamePermissionOperationsTests(TransactionTestCase):
    available_apps = [
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "auth_tests",
    ]

    def setUp(self):
        # `contenttypes` is one of the apps for which the migrations are skipped in the tests setup.
        # Fake the migrations to record them in the database and have them be part of the migration plan.
        call_command(
            "migrate",
            "contenttypes",
            database="default",
            interactive=False,
            verbosity=0,
            fake=True,
        )
        call_command(
            "migrate",
            "auth_tests",
            "0001_initial",
            fake=True,
            database="default",
            interactive=False,
            verbosity=0,
        )
        call_command(
            "migrate",
            "auth_tests",
            "zero",
            database="default",
            interactive=False,
            verbosity=0,
        )

    def test_permissions_renamed_with_new_verbose_name(self):
        call_command(
            "migrate",
            "auth_tests",
            "0002_altered_model_options",
            database="default",
            interactive=False,
            verbosity=0,
        )

    def test_permissions_renamed_with_old_verbose_name_after_backward_migration(self):
        call_command(
            "migrate",
            "auth_tests",
            "0002_altered_model_options",
            database="default",
            interactive=False,
            verbosity=0,
        )
        call_command(
            "migrate",
            "auth_tests",
            "0001",
            database="default",
            interactive=False,
            verbosity=0,
        )


@override_settings(
    MIGRATION_MODULES=dict(
        settings.MIGRATION_MODULES,
        auth="django.contrib.auth.migrations",
        contenttypes="django.contrib.contenttypes.migrations",
        auth_tests="auth_tests.operations_migrations",
    )
)
class CreatePermissionOperationsTests(TransactionTestCase):
    available_apps = [
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "auth_tests",
    ]

    def setUp(self):
        # `contenttypes` is one of the apps for which the migrations are skipped in the tests setup.
        # Fake the migrations to record them in the database and have them be part of the migration plan.
        call_command(
            "migrate",
            "contenttypes",
            database="default",
            interactive=False,
            verbosity=0,
            fake=True,
        )
        call_command(
            "migrate",
            "auth_tests",
            fake=True,
            database="default",
            interactive=False,
            verbosity=0,
        )
        call_command(
            "migrate",
            "auth_tests",
            "zero",
            database="default",
            interactive=False,
            verbosity=0,
        )

    def test_permissions_created_for_new_verbose_name(self):
        call_command(
            "migrate", "auth_tests", database="default", interactive=False, verbosity=0
        )
