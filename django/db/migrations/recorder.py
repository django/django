from __future__ import unicode_literals

from django.apps.registry import Apps
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now


class MigrationRecorder(object):
    """
    Deals with storing migration records in the database.

    Because this table is actually itself used for dealing with model
    creation, it's the one thing we can't do normally via syncdb or migrations.
    We manually handle table creation/schema updating (using schema backend)
    and then have a floating model to do queries with.

    If a migration is unapplied its row is removed from the table. Having
    a row in the table always means a migration is applied.
    """

    @python_2_unicode_compatible
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

    def __init__(self, connection):
        self.connection = connection

    @property
    def migration_qs(self):
        return self.Migration.objects.using(self.connection.alias)

    def ensure_schema(self):
        """
        Ensures the table exists and has the correct schema.
        """
        # If the table's there, that's fine - we've never changed its schema
        # in the codebase.
        if self.Migration._meta.db_table in self.connection.introspection.get_table_list(self.connection.cursor()):
            return
        # Make the table
        with self.connection.schema_editor() as editor:
            editor.create_model(self.Migration)

    def applied_migrations(self):
        """
        Returns a set of (app, name) of applied migrations.
        """
        self.ensure_schema()
        return set(tuple(x) for x in self.migration_qs.values_list("app", "name"))

    def record_applied(self, app, name):
        """
        Records that a migration was applied.
        """
        self.ensure_schema()
        self.migration_qs.create(app=app, name=name)

    def record_unapplied(self, app, name):
        """
        Records that a migration was unapplied.
        """
        self.ensure_schema()
        self.migration_qs.filter(app=app, name=name).delete()

    def flush(self):
        """
        Deletes all migration records. Useful if you're testing migrations.
        """
        self.migration_qs.all().delete()
