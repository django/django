from freedom.db.backends.creation import NO_DB_ALIAS
from freedom.db.backends.postgresql_psycopg2.base import DatabaseWrapper as Psycopg2DatabaseWrapper
from freedom.contrib.gis.db.backends.postgis.creation import PostGISCreation
from freedom.contrib.gis.db.backends.postgis.introspection import PostGISIntrospection
from freedom.contrib.gis.db.backends.postgis.operations import PostGISOperations
from freedom.contrib.gis.db.backends.postgis.schema import PostGISSchemaEditor


class DatabaseWrapper(Psycopg2DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        if kwargs.get('alias', '') != NO_DB_ALIAS:
            self.creation = PostGISCreation(self)
            self.ops = PostGISOperations(self)
            self.introspection = PostGISIntrospection(self)

    def schema_editor(self, *args, **kwargs):
        "Returns a new instance of this backend's SchemaEditor"
        return PostGISSchemaEditor(self, *args, **kwargs)
