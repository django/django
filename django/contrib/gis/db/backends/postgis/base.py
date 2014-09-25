from django.db.backends.creation import NO_DB_ALIAS
from django.db.backends.postgresql_psycopg2.base import (
    DatabaseWrapper as Psycopg2DatabaseWrapper,
    DatabaseFeatures as Psycopg2DatabaseFeatures
)
from django.contrib.gis.db.backends.base import BaseSpatialFeatures
from django.contrib.gis.db.backends.postgis.creation import PostGISCreation
from django.contrib.gis.db.backends.postgis.introspection import PostGISIntrospection
from django.contrib.gis.db.backends.postgis.operations import PostGISOperations
from django.contrib.gis.db.backends.postgis.schema import PostGISSchemaEditor


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
