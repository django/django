import os
import subprocess
import sys
import shutil
import tempfile
from io import StringIO

from django.core.management import call_command

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = 'Manage migrations: delete or update migrations files and database records'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['restore-init', 'delete', 'update'], help='Action to perform on migrations')
        parser.add_argument('app_label', nargs='?', help='Specify the app to perform the action on')
        parser.add_argument('migration_name', nargs='*', default='all', help='Specify the migration to perform the action on')
        parser.add_argument('--auto_migrate', nargs='?', help='Automatically run makemigrations and migrate after restoring initial migrations')
        parser.add_argument('--database', default=DEFAULT_DB_ALIAS, help='Specify the database to use')

    def handle(self, *args, **options):
        action = options['action']
        app_label = options['app_label']
        migration_name = options['migration_name']
        database = options['database']
        auto_migrate = options['auto_migrate']
        connection = connections[database]
        loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)

        if action == 'delete':
            if not app_label:
                raise CommandError("You must specify an app label for the delete action.")
            delete_migration_names = None
            if migration_name != "all":
                delete_migration_names = migration_name.split(',')
            self.delete_migrations(loader, recorder, app_label, delete_migration_names)
        elif action == 'restore-init':
            self.empty_and_init_migrations(loader, recorder, auto_migrate)

    def delete_migrations(self, loader, recorder, app_label, delete_migration_names=None, out_stream=True):
        # TODO: optimize this function for better performance and output
        def _log(msg, ending="\n"):
            self.stdout.write(msg, ending=ending) if out_stream else None

        if app_label not in loader.migrated_apps:
            raise CommandError(f"App '{app_label}' does not have any migrations.")

        migrations = [(key, value) for key, value in loader.disk_migrations.items() if key[0] == app_label]

        if delete_migration_names:
            migrations = [mig for mig in migrations if mig[0][1] in delete_migration_names]

        backup_dir = tempfile.mkdtemp()
        deleted_migrations = []

        _log(f"Found {len(migrations)} migrations that need deleted for '{app_label}':")
        try:
            for app_migration_tuple, migration in migrations:
                _log(f"  Deleting migration  {migration}...", " ")
                # 拼接migration文件的路径
                migration_file = os.path.join(app_label, 'migrations', migration.name + '.py')
                # 拼接migration二进制文件的路径
                migration_binary_file = os.path.join(app_label, 'migrations', '__pycache__', migration.name + f'.{sys.implementation.cache_tag}' + '.pyc')

                # 备份并删除迁移文件
                if os.path.exists(migration_file):
                    shutil.copy(migration_file, os.path.join(backup_dir, os.path.basename(migration_file)))
                    os.remove(migration_file)
                if os.path.exists(migration_binary_file):
                    shutil.copy(migration_binary_file, os.path.join(backup_dir, os.path.basename(migration_binary_file)))
                    os.remove(migration_binary_file)

                # 备份数据库中的记录
                deleted_migrations.append((app_label, migration.name))

                # 删除数据库中的记录
                recorder.migration_qs.filter(app=app_label, name=migration.name).delete()
                _log("OK")

        except Exception as e:
            _log(f"  Failed to delete migration: {e}")
            _log("  Rolling back changes...")
            # 恢复迁移文件
            for backup_file in os.listdir(backup_dir):
                shutil.move(os.path.join(backup_dir, backup_file), os.path.join(app_label, 'migrations', backup_file))
            # 恢复数据库记录
            for app, name in deleted_migrations:
                recorder.migration_qs.create(app=app, name=name)
            raise CommandError("Rollback completed due to errors.")

        finally:
            # 删除备份目录
            shutil.rmtree(backup_dir, ignore_errors=True)

    def call_command_silently(self, command_name, *args, **kwargs):
        # 调用其他manage命令并抑制输出
        out = StringIO()
        try:
            call_command(command_name, *args, stdout=out, **kwargs)
        except Exception as e:
            self.stdout.write("\n")
            self.stderr.write(out.getvalue())
            raise CommandError(f"Failed to run command '{command_name}': {e}")
        return out.getvalue()

    def empty_and_init_migrations(self, loader, recorder, auto_migrate=None):
        # TODO: add single or list of apps to restore initial migrations
        try:
            for app in apps.get_app_configs():
                self.stdout.write(f"Restoring initial migrations for app '{app.label}':")
                self.delete_migrations(loader, recorder, app.label, out_stream=False)
            # 重新执行makemigrations和migrate命令，其中migrate命令应由用户决定是否执行，默认不执行
            self.stdout.write("  Running 'makemigrations'...", ending=" ")
            self.call_command_silently('makemigrations')
            self.stdout.write("OK")
            if auto_migrate == "1":
                self.stdout.write("  Running 'migrate'...", ending=" ")
                self.call_command_silently('migrate')
                self.stdout.write("OK")
        except Exception as e:
            raise CommandError(f"Failed to restore initial migrations: {e}")
