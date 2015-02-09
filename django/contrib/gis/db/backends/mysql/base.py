from django.db.backends.mysql.base import \
    DatabaseWrapper as MySQLDatabaseWrapper

from .creation import MySQLCreation
from .features import DatabaseFeatures
from .introspection import MySQLIntrospection
from .operations import MySQLOperations
from .schema import MySQLGISSchemaEditor


class DatabaseWrapper(MySQLDatabaseWrapper):
    SchemaEditorClass = MySQLGISSchemaEditor

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures(self)
        self.creation = MySQLCreation(self)
        self.ops = MySQLOperations(self)
        self.introspection = MySQLIntrospection(self)
