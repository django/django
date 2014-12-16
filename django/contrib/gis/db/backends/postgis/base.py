from django.conf import settings
from django.db.backends import NO_DB_ALIAS
from django.db.backends.postgresql_psycopg2.base import (
    DatabaseWrapper as Psycopg2DatabaseWrapper,
    DatabaseFeatures as Psycopg2DatabaseFeatures
)
from django.contrib.gis.db.backends.base import BaseSpatialFeatures
from django.contrib.gis.db.backends.postgis.creation import PostGISCreation
from django.contrib.gis.db.backends.postgis.introspection import PostGISIntrospection
from django.contrib.gis.db.backends.postgis.operations import PostGISOperations
from django.contrib.gis.db.backends.postgis.schema import PostGISSchemaEditor
from django.utils.functional import cached_property


class DatabaseFeatures(BaseSpatialFeatures, Psycopg2DatabaseFeatures):
    supports_3d_functions = True
    supports_left_right_lookups = True


class DatabaseWrapper(Psycopg2DatabaseWrapper):
    SchemaEditorClass = PostGISSchemaEditor

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        if kwargs.get('alias', '') != NO_DB_ALIAS:
            self.features = DatabaseFeatures(self)
            self.creation = PostGISCreation(self)
            self.ops = PostGISOperations(self)
            self.introspection = PostGISIntrospection(self)

    @cached_property
    def template_postgis(self):
        template_postgis = getattr(settings, 'POSTGIS_TEMPLATE', 'template_postgis')
        with self._nodb_connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s LIMIT 1;', (template_postgis,))
            if cursor.fetchone():
                return template_postgis
        return None

    def prepare_database(self):
        super(DatabaseWrapper, self).prepare_database()
        if self.template_postgis is None:
            # Check that postgis extension is installed on PostGIS >= 2
            with self.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
