from django.db.backends.oracle.base import \
    DatabaseWrapper as OracleDatabaseWrapper

from .features import DatabaseFeatures
from .introspection import OracleIntrospection
from .operations import OracleOperations
from .schema import OracleGISSchemaEditor


class DatabaseWrapper(OracleDatabaseWrapper):
    SchemaEditorClass = OracleGISSchemaEditor

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.features = DatabaseFeatures(self)
        self.ops = OracleOperations(self)
        self.introspection = OracleIntrospection(self)
