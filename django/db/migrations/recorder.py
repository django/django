from django.core.apps.cache import AppCache
from django.db import models
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

    class Migration(models.Model):
        app = models.CharField(max_length=255)
        name = models.CharField(max_length=255)
        applied = models.DateTimeField(default=now)

        class Meta:
            app_cache = AppCache()
            app_label = "migrations"
            db_table = "django_migrations"

    def __init__(self, connection):
        self.connection = connection

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
        return set(tuple(x) for x in self.Migration.objects.values_list("app", "name"))

    def record_applied(self, app, name):
        """
        Records that a migration was applied.
        """
        self.ensure_schema()
        self.Migration.objects.create(app=app, name=name)

    def record_unapplied(self, app, name):
        """
        Records that a migration was unapplied.
        """
        self.ensure_schema()
        self.Migration.objects.filter(app=app, name=name).delete()

    @classmethod
    def flush(cls):
        """
        Deletes all migration records. Useful if you're testing migrations.
        """
        cls.Migration.objects.all().delete()
