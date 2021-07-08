from django.db.backends.base.base import NO_DB_ALIAS
from django.db.backends.postgresql.base import (
    DatabaseWrapper as Psycopg2DatabaseWrapper,
)

from .features import DatabaseFeatures
from .introspection import PostGISIntrospection
from .operations import PostGISOperations
from .schema import PostGISSchemaEditor


class DatabaseWrapper(Psycopg2DatabaseWrapper):
    SchemaEditorClass = PostGISSchemaEditor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('alias', '') != NO_DB_ALIAS:
            self.features = DatabaseFeatures(self)
            self.ops = PostGISOperations(self)
            self.introspection = PostGISIntrospection(self)

    def prepare_database(self):
        super().prepare_database()
        # Check that postgis extension is installed.
        with self.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
