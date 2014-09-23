from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper
from django.contrib.gis.db.backends.mysql.creation import MySQLCreation
from django.contrib.gis.db.backends.mysql.introspection import MySQLIntrospection
from django.contrib.gis.db.backends.mysql.operations import MySQLOperations
from django.contrib.gis.db.backends.mysql.schema import MySQLGISSchemaEditor


class DatabaseWrapper(MySQLDatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.creation = MySQLCreation(self)
        self.ops = MySQLOperations(self)
        self.introspection = MySQLIntrospection(self)

    def schema_editor(self, *args, **kwargs):
        "Returns a new instance of this backend's SchemaEditor"
        return MySQLGISSchemaEditor(self, *args, **kwargs)
