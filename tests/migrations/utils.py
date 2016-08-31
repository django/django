from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.utils.decorators import ContextDecorator


class without_django_migrations_table(ContextDecorator):
    """
    Rename the django_migrations table to simulate its absence for the duration
    of the context manager.
    """
    def __init__(self):
        self.old_table_name = MigrationRecorder.Migration._meta.db_table
        self.temp_table_name = MigrationRecorder.Migration._meta.db_table + '_tmp'

    def __enter__(self):
        with connection.schema_editor() as editor:
            editor.alter_db_table(MigrationRecorder.Migration, self.old_table_name, self.temp_table_name)

    def __exit__(self, exc_type, exc_value, traceback):
        with connection.schema_editor() as editor:
            editor.alter_db_table(MigrationRecorder.Migration, self.temp_table_name, self.old_table_name)
