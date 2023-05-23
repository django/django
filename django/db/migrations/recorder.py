from django.apps.registry import Apps
from django.db import DatabaseError, models
from django.utils.functional import classproperty
from django.utils.timezone import now

from .exceptions import MigrationSchemaMissing


class MigrationRecorder:
    """
    Deal with storing migration records in the database.

    Because this table is actually itself used for dealing with model
    creation, it's the one thing we can't do normally via migrations.
    We manually handle table creation/schema updating (using schema backend)
    and then have a floating model to do queries with.

    If a migration is unapplied its row is removed from the table. Having
    a row in the table always means a migration is applied.
    """

    _migration_class = None

    @classproperty
    def Migration(cls):
        """
        Lazy load to avoid AppRegistryNotReady if installed apps import
        MigrationRecorder.
        """
        if cls._migration_class is None:

            class Migration(models.Model):
                app = models.CharField(max_length=255)
                name = models.CharField(max_length=255)
                applied = models.DateTimeField(default=now)

                class Meta:
                    apps = Apps()
                    app_label = "migrations"
                    db_table = "django_migrations"

                def __str__(self):
                    return "Migration %s for %s" % (self.name, self.app)

            cls._migration_class = Migration
        return cls._migration_class

    def __init__(self, connection):
        self.connection = connection
        self._has_table = False

    @property
    def migration_qs(self):
        return self.Migration.objects.using(self.connection.alias)

    def has_table(self):
        """Return True if the django_migrations table exists."""
        # If the migrations table has already been confirmed to exist, don't
        # recheck it's existence.
        if self._has_table:
            return True
        # It hasn't been confirmed to exist, recheck.
        with self.connection.cursor() as cursor:
            tables = self.connection.introspection.table_names(cursor)

        self._has_table = self.Migration._meta.db_table in tables
        return self._has_table

    def ensure_schema(self):
        """Ensure the table exists and has the correct schema."""
        # If the table's there, that's fine - we've never changed its schema
        # in the codebase.
        if self.has_table():
            return
        # Make the table
        try:
            with self.connection.schema_editor() as editor:
                editor.create_model(self.Migration)
        except DatabaseError as exc:
            raise MigrationSchemaMissing(
                "Unable to create the django_migrations table (%s)" % exc
            )

    def applied_migrations(self):
        """
        Return a dict mapping (app_name, migration_name) to Migration instances
        for all applied migrations.
        """
        if self.has_table():
            return {
                (migration.app, migration.name): migration
                for migration in self.migration_qs
            }
        else:
            # If the django_migrations table doesn't exist, then no migrations
            # are applied.
            return {}

    def record_applied(self, app, name):
        """Record that a migration was applied."""
        self.ensure_schema()
        self.migration_qs.create(app=app, name=name)

    def record_unapplied(self, app, name):
        """Record that a migration was unapplied."""
        self.ensure_schema()
        self.migration_qs.filter(app=app, name=name).delete()

    def flush(self):
        """Delete all migration records. Useful for testing migrations."""
        self.migration_qs.all().delete()
