import io
import textwrap
from pathlib import Path

from migrations.test_base import MigrationTestBase

from django.core.exceptions import FieldError
from django.core.management import call_command
from django.test import TransactionTestCase
from django.test.utils import override_settings


class AutodetectorUnmanagedModelTest(MigrationTestBase, TransactionTestCase):
    """Regression test for bug in autodetector with FK to managed=False model."""

    # TODO: it should also test
    #       1) [x] create new "managed=False" model with FK
    #       2) [ ] add new field FK for already migrated(created) "managed=False" model
    #       3) [ ] drop field FK for already migrated(created) "managed=False" model

    @override_settings(
        INSTALLED_APPS=["migrations.migrations_test_apps.unmanaged_models"]
    )
    def test_runpython_crashes_on_missing_fk_field(self):
        out = io.StringIO()
        with self.temporary_migration_module("unmanaged_models") as tmp_dir:
            call_command("makemigrations", "unmanaged_models")
            call_command("migrate", "unmanaged_models")
            with open(Path(tmp_dir) / "0002_custom.py", "w") as custom_migration_file:
                custom_migration_content = textwrap.dedent(
                    """
                from django.db import migrations


                def forwards_func(apps, schema_editor):
                    klass_Boo = apps.get_model("unmanaged_models", "Boo")
                    klass_Boo.objects.filter(foo=1)


                class Migration(migrations.Migration):

                    dependencies = [
                        ('unmanaged_models', '0001_initial'),
                    ]

                    operations = [
                        migrations.RunPython(
                            forwards_func,
                            reverse_code=migrations.RunPython.noop
                        ),
                    ]
                """
                )
                custom_migration_file.write(custom_migration_content)
            try:
                call_command("migrate", "unmanaged_models", stdout=out)
            except FieldError:
                # this is the bug from #29177, it can not find FK in managed=False model
                pass
            self.assertIn("OK", out.getvalue())
