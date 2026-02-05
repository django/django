import io
import textwrap
from pathlib import Path

from migrations.test_base import MigrationTestBase

from django.core.exceptions import FieldError
from django.core.management import call_command
from django.test import TransactionTestCase
from django.test.utils import override_settings


class AutodetectorUnmanagedModelTest(MigrationTestBase, TransactionTestCase):
    """Regression test for bug #29177 in autodetector with
    FK to managed=False model."""

    # Consider also other cases to test, but the
    # 'test_create_model_migrate_crashes_on_missing_fk' is the proove of a bug

    @override_settings(
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        INSTALLED_APPS=["migrations.migrations_test_apps.unmanaged_model_with_fk"],
    )
    def test_create_model_migrate_crashes_on_missing_fk(self):
        out = io.StringIO()
        with self.temporary_migration_module("unmanaged_model_with_fk") as tmp_dir:
            call_command("makemigrations", "unmanaged_model_with_fk", verbosity=0)
            call_command("migrate", "unmanaged_model_with_fk", verbosity=0)
            with open(Path(tmp_dir) / "0002_custom.py", "w") as custom_migration_file:
                custom_migration_content = textwrap.dedent("""
                from django.db import migrations


                def forwards_func(apps, schema_editor):
                    klass_Boo = apps.get_model("unmanaged_model_with_fk", "Boo")
                    klass_Boo.objects.filter(foo=1)


                class Migration(migrations.Migration):

                    dependencies = [
                        ('unmanaged_model_with_fk', '0001_initial'),
                    ]

                    operations = [
                        migrations.RunPython(
                            forwards_func,
                            reverse_code=migrations.RunPython.noop
                        ),
                    ]
                """)
                custom_migration_file.write(custom_migration_content)
            try:
                call_command("migrate", "unmanaged_model_with_fk", stdout=out)
            except FieldError:
                # it can not find FK in managed=False model
                pass
            self.assertIn("OK", out.getvalue())

    @override_settings(
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        INSTALLED_APPS=["migrations.migrations_test_apps.unmanaged_model_with_fk"],
    )
    def test_add_field_operation_is_detected(self):
        out = io.StringIO()
        initial_migration_content = textwrap.dedent("""
            from django.db import migrations, models


            class Migration(migrations.Migration):

                initial = True

                dependencies = [
                ]

                operations = [
                    migrations.CreateModel(
                        name='Foo',
                        fields=[
                            (
                                'id',
                                models.AutoField(
                                    auto_created=True,
                                    primary_key=True,
                                    serialize=False,
                                    verbose_name='ID'
                                )
                            ),
                        ],
                        options={
                            'managed': True,
                        },
                    ),
                    migrations.CreateModel(
                        name='Boo',
                        fields=[
                            (
                                'id',
                                models.AutoField(
                                    auto_created=True,
                                    primary_key=True,
                                    serialize=False,
                                    verbose_name='ID'
                                )
                            ),
                        ],
                        options={
                            'managed': False,
                        },
                    ),
                ]
            """)
        with self.temporary_migration_module("unmanaged_model_with_fk") as tmp_dir:
            with open(Path(tmp_dir) / "0001_initial.py", "w") as initial_migration_file:
                initial_migration_file.write(initial_migration_content)
            call_command(
                "makemigrations",
                "unmanaged_model_with_fk",
                dry_run=True,
                verbosity=3,
                stdout=out,
            )
        # explanation: currently as a side effect of a bug in #29177,
        #              there is: "No changes detected in app...", but
        #              AddField( ... name='foo' ...) should be there
        migration_content = out.getvalue()
        add_field_content = migration_content[migration_content.find("AddField") :]
        add_field_content = add_field_content[: add_field_content.find(")") + 1]
        self.assertIn("AddField", add_field_content)
        self.assertIn("name='foo'", add_field_content)

    @override_settings(
        DEFAULT_AUTO_FIELD="django.db.models.AutoField",
        INSTALLED_APPS=["migrations.migrations_test_apps.unmanaged_model_with_fk"],
    )
    def test_remove_field_operation_is_detected(self):
        out = io.StringIO()
        initial_migration_content = textwrap.dedent("""
            from django.db import migrations, models


            class Migration(migrations.Migration):

                initial = True

                dependencies = [
                ]

                operations = [
                    migrations.CreateModel(
                        name='Foo',
                        fields=[
                            (
                                'id',
                                models.AutoField(
                                    auto_created=True,
                                    primary_key=True,
                                    serialize=False,
                                    verbose_name='ID'
                                )
                            ),
                        ],
                        options={
                            'managed': True,
                        },
                    ),
                    migrations.CreateModel(
                        name='Boo',
                        fields=[
                            (
                                'id',
                                models.AutoField(
                                    auto_created=True,
                                    primary_key=True,
                                    serialize=False,
                                    verbose_name='ID'
                                )
                            ),
                            (
                                'foo',
                                models.ForeignKey(
                                    on_delete=models.deletion.CASCADE,
                                    to='unmanaged_models.foo',
                                )
                            ),
                            (
                                'fk_foo',
                                models.ForeignKey(
                                    on_delete=models.deletion.CASCADE,
                                    to='unmanaged_models.foo',
                                )
                            ),
                        ],
                        options={
                            'managed': False,
                        },
                    ),
                ]
            """)
        with self.temporary_migration_module("unmanaged_model_with_fk") as tmp_dir:
            with open(Path(tmp_dir) / "0001_initial.py", "w") as initial_migration_file:
                initial_migration_file.write(initial_migration_content)
            call_command(
                "makemigrations",
                "unmanaged_model_with_fk",
                dry_run=True,
                verbosity=3,
                stdout=out,
            )
        # explanation: currently as a side effect of a bug in #29177,
        #              there is: "No changes detected in app...", but
        #              RemoveField( ... name='fk_foo' ...) should be there
        migration_content = out.getvalue()
        remove_field_content = migration_content[
            migration_content.find("RemoveField") :
        ]
        remove_field_content = remove_field_content[
            : remove_field_content.find(")") + 1
        ]
        self.assertIn("RemoveField", remove_field_content)
        self.assertIn("name='fk_foo'", remove_field_content)
